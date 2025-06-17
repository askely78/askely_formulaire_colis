from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///colis.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Colis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    destinataire = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(200), nullable=False)
    statut = db.Column(db.String(100), default='En attente')

class Transporteur(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    numero_whatsapp = db.Column(db.String(20), unique=True, nullable=False)
    date_depart = db.Column(db.String(20), nullable=False)
    ville_depart = db.Column(db.String(100), nullable=False)
    ville_arrivee = db.Column(db.String(100), nullable=False)

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return "Bienvenue sur Askely Express"

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        numero = request.form['numero']
        destinataire = request.form['destinataire']
        adresse = request.form['adresse']
        statut = request.form['statut']
        colis = Colis(numero=numero, destinataire=destinataire, adresse=adresse, statut=statut)
        db.session.add(colis)
        db.session.commit()
        return "Colis ajouté avec succès !"
    return render_template('admin.html')

@app.route('/suivi', methods=['GET', 'POST'])
def suivi():
    colis = None
    if request.method == 'POST':
        numero = request.form['numero']
        colis = Colis.query.filter_by(numero=numero).first()
    return render_template('suivi.html', colis=colis)

@app.route('/register_transporteur', methods=['GET', 'POST'])
def register_transporteur():
    if request.method == 'POST':
        nom = request.form['nom']
        numero_whatsapp = request.form['numero_whatsapp']
        date_depart = request.form['date_depart']
        ville_depart = request.form['ville_depart']
        ville_arrivee = request.form['ville_arrivee']
        t = Transporteur(
            nom=nom,
            numero_whatsapp=numero_whatsapp,
            date_depart=date_depart,
            ville_depart=ville_depart,
            ville_arrivee=ville_arrivee
        )
        db.session.add(t)
        db.session.commit()
        return "Transporteur inscrit avec succès"
    return """<form method='POST'>
        Nom: <input type='text' name='nom'><br>
        Numéro WhatsApp: <input type='text' name='numero_whatsapp'><br>
        Date de départ: <input type='text' name='date_depart'><br>
        Ville de départ: <input type='text' name='ville_depart'><br>
        Ville d'arrivée: <input type='text' name='ville_arrivee'><br>
        <input type='submit' value='S'inscrire'>
    </form>"""

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp():
    incoming_msg = request.values.get('Body', '').strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ['bonjour', 'hello', 'salut']:
        msg.body(
            "👋 Bienvenue chez *Askely Express* !
Répondez par :
"
            "1. Envoyer un colis 📦
"
            "2. Devenir transporteur 🚐
"
            "3. Suivre un colis 🔍"
        )
    elif incoming_msg == '1':
        msg.body("📦 Pour envoyer un colis, veuillez visiter : https://askely-express.onrender.com/admin")
    elif incoming_msg == '2':
        msg.body("🚐 Pour devenir transporteur, visitez : https://askely-express.onrender.com/register_transporteur")
    elif incoming_msg == '3':
        msg.body("🔍 Pour suivre un colis, visitez : https://askely-express.onrender.com/suivi")
    else:
        msg.body("❌ Je n’ai pas compris. Répondez par :
1, 2 ou 3.")

    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)