from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import psycopg2, psycopg2.extras
import os

# ────────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")           # valeur rendue par Render
PORT         = int(os.getenv("PORT", 10000))       # Render injecte aussi PORT

# ────────────────────────────────────────────────────────────────────────────────
# UTILITAIRES BD
# ────────────────────────────────────────────────────────────────────────────────
def get_conn():
    """Connexion PostgreSQL (RealDictCursor pour dict-like)."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def init_db():
    """Crée les tables si elles n’existent pas."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transporteurs (
            id              SERIAL PRIMARY KEY,
            nom             TEXT,
            ville_depart    TEXT,
            ville_arrivee   TEXT,
            date_depart     TEXT,
            numero_whatsapp TEXT,
            paiement        TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS colis (
            id              SERIAL PRIMARY KEY,
            expediteur      TEXT,
            destinataire    TEXT,
            date_envoi      TEXT,
            transporteur_id INTEGER REFERENCES transporteurs(id)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# ────────────────────────────────────────────────────────────────────────────────
# ROUTE D’ACCUEIL – évite le 404 sur /
# ────────────────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return "✅ Askely Express (Flask + PostgreSQL) est en ligne."

# Mémoire courte pour l’utilisateur (clé = numéro WhatsApp)
user_cache = {}

# ────────────────────────────────────────────────────────────────────────────────
# WEBHOOK WHATSAPP
# ────────────────────────────────────────────────────────────────────────────────
@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp():
    incoming = request.values.get("Body", "").strip()
    num      = request.values.get("From", "")                   # ex: whatsapp:+2126...
    txt      = incoming.lower()

    resp = MessagingResponse()
    msg  = resp.message()

    # ── MENU PRINCIPAL ────────────────────────────────────────────────────────
    if txt in {"bonjour", "salut", "hello"}:
        msg.body(
            "👋 Bonjour ! Bienvenue chez *Askely Express* 🇲🇦\n\n"
            "Que souhaitez-vous faire ? Répondez avec :\n"
            "1️⃣ Envoyer un colis\n"
            "2️⃣ Devenir transporteur\n"
            "3️⃣ Suivre un colis"
        )
        user_cache.pop(num, None)                       # reset éventuel
        return str(resp)

    # ══════════════════════════════════════════════════════════════════════════
    # 1) ENVOI DE COLIS
    # ══════════════════════════════════════════════════════════════════════════
    cache = user_cache.get(num, {})
    step  = cache.get("step")

    if txt.startswith("1") or "envoyer un colis" in txt and not step:
        user_cache[num] = {"step": "colis_info"}
        msg.body(
            "📦 Veuillez envoyer les infos du colis (1 seul message) :\n"
            "`Nom expéditeur - Nom destinataire - Date (JJ/MM/AAAA)`"
        )
        return str(resp)

    if step == "colis_info" and "-" in txt:
        try:
            exp, dest, date_envoi = [x.strip() for x in incoming.split("-")]
        except ValueError:
            msg.body("❌ Format invalide. Réessayez (3 éléments séparés par `-`).")
            return str(resp)

        # stocker dans cache
        user_cache[num] = {
            "step":        "choix_transporteur",
            "expediteur":  exp,
            "destinataire":dest,
            "date":        date_envoi
        }

        # chercher transporteurs
        conn = get_conn(); cur = conn.cursor()
        cur.execute(
            "SELECT id, nom, ville_depart, ville_arrivee "
            "FROM transporteurs WHERE date_depart = %s",
            (date_envoi,)
        )
        dispo = cur.fetchall(); cur.close(); conn.close()

        if not dispo:
            msg.body("❌ Aucun transporteur dispo à cette date. Envoyez une autre date.")
            user_cache.pop(num, None)
            return str(resp)

        # afficher la liste
        listing = "\n".join(
            f"*{t['id']}* – {t['nom']} ({t['ville_depart']} ➡️ {t['ville_arrivee']})"
            for t in dispo
        )
        msg.body(
            f"🚚 Transporteurs disponibles le {date_envoi} :\n{listing}\n\n"
            "Répondez : `Choisir <ID>`"
        )
        return str(resp)

    # Choix du transporteur
    if txt.startswith("choisir") and step == "choix_transporteur":
        try:
            t_id = int(txt.split()[1])
        except (IndexError, ValueError):
            msg.body("❌ Format : `Choisir <ID>`")
            return str(resp)

        exp  = cache["expediteur"]; dest = cache["destinataire"]; date = cache["date"]
        conn = get_conn(); cur = conn.cursor()

        # Vérifier le transporteur
        cur.execute("SELECT nom, numero_whatsapp FROM transporteurs WHERE id=%s", (t_id,))
        tr = cur.fetchone()
        if not tr:
            msg.body("❌ ID transporteur introuvable.")
            cur.close(); conn.close(); user_cache.pop(num, None)
            return str(resp)

        # Enregistrement colis
        cur.execute(
            "INSERT INTO colis (expediteur, destinataire, date_envoi, transporteur_id) "
            "VALUES (%s,%s,%s,%s) RETURNING id",
            (exp, dest, date, t_id)
        )
        colis_id = cur.fetchone()["id"]
        conn.commit(); cur.close(); conn.close()
        user_cache.pop(num, None)

        msg.body(
            f"✅ Colis *#{colis_id}* enregistré avec *{tr['nom']}*.\n"
            f"📲 Contactez-le : {tr['numero_whatsapp']}"
        )
        return str(resp)

    # ══════════════════════════════════════════════════════════════════════════
    # 2) INSCRIPTION TRANSPORTEUR
    # ══════════════════════════════════════════════════════════════════════════
    if txt.startswith("2") or "devenir transporteur" in txt:
        msg.body(
            "🚚 Envoyez vos infos (1 seul message) :\n"
            "`Nom - Ville départ - Ville arrivée - Date (JJ/MM/AAAA) - WhatsApp - Paiement OK`"
        )
        user_cache[num] = {"step": "insc_transporteur"}
        return str(resp)

    if user_cache.get(num, {}).get("step") == "insc_transporteur" and txt.count("-") == 5:
        nom, vdep, varr, date_dep, numero, paiement = [x.strip() for x in incoming.split("-")]
        conn = get_conn(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO transporteurs "
            "(nom, ville_depart, ville_arrivee, date_depart, numero_whatsapp, paiement) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (nom, vdep, varr, date_dep, numero, paiement)
        )
        conn.commit(); cur.close(); conn.close()
        user_cache.pop(num, None)
        msg.body("✅ Inscription réussie ! Vous recevrez les notifications des clients.")
        return str(resp)

    # ══════════════════════════════════════════════════════════════════════════
    # 3) SUIVI DE COLIS PAR NOM EXPÉDITEUR
    # ══════════════════════════════════════════════════════════════════════════
    if txt.startswith("3") or "suivre un colis" in txt:
        msg.body("🔍 Envoyez *le nom d’expéditeur* pour voir le dernier colis.")
        return str(resp)

    if len(txt) > 1:  # recherche par nom
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.date_envoi, t.nom AS tr_nom, t.numero_whatsapp
            FROM colis c
            JOIN transporteurs t ON c.transporteur_id = t.id
            WHERE LOWER(c.expediteur) LIKE %s
            ORDER BY c.id DESC LIMIT 1
        """, (f"%{txt}%",))
        row = cur.fetchone(); cur.close(); conn.close()
        if row:
            msg.body(
                f"📦 Colis #{row['id']} (date {row['date_envoi']}) avec transporteur {row['tr_nom']}.\n"
                f"📲 Contact : {row['numero_whatsapp']}"
            )
        else:
            msg.body("❌ Aucun colis correspondant à ce nom.")
        return str(resp)

    # ── Catch-all ────────────────────────────────────────────────────────────
    msg.body("🤖 Je n’ai pas compris. Envoyez `Bonjour` pour voir les options.")
    return str(resp)

# ────────────────────────────────────────────────────────────────────────────────
# Lancement
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=PORT, debug=True)
@app.route("/")
def home():
    return "✅ Askely Express fonctionne avec PostgreSQL et WhatsApp !"
