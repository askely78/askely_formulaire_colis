
from flask import Flask, request, render_template, redirect, url_for
import sqlite3

app = Flask(__name__)

# Connexion à la base
def get_db_connection():
    conn = sqlite3.connect('colis.db')
    conn.row_factory = sqlite3.Row
    return conn

# Route admin - ajouter colis
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        numero = request.form['numero']
        client = request.form['client']
        destination = request.form['destination']
        statut = request.form['statut']

        conn = get_db_connection()
        conn.execute('INSERT INTO colis (numero, client, destination, statut) VALUES (?, ?, ?, ?)',
                     (numero, client, destination, statut))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    return render_template('admin.html')

# Route utilisateur - suivi de colis
@app.route('/suivi', methods=['GET', 'POST'])
def suivi():
    if request.method == 'POST':
        numero = request.form['numero']
        conn = get_db_connection()
        colis = conn.execute('SELECT * FROM colis WHERE numero = ?', (numero,)).fetchone()
        conn.close()
        return render_template('suivi.html', colis=colis)
    return render_template('suivi.html', colis=None)

if __name__ == '__main__':
    app.run(debug=True, port=10000)
