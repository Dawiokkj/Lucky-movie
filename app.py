"""
App web da Roleta de Filmes do Letterboxd.

Rode com:
    python app.py

Depois abra http://127.0.0.1:5000 no navegador.

Dependencias:
    pip install flask curl_cffi beautifulsoup4
"""

from flask import Flask, render_template, request, jsonify

from letterboxd_scraper import LetterboxdRoulette, extrair_username
from curl_cffi import requests as curl_requests

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sortear", methods=["POST"])
def sortear():
    data = request.get_json(silent=True) or {}
    link_usuario = (data.get("usuario") or "").strip()
    link_lista = (data.get("link") or "").strip()

    if not link_usuario:
        return jsonify({"erro": "Informe o link (ou nome) do seu perfil no Letterboxd."}), 400
    if not link_lista:
        return jsonify({"erro": "Informe o link da lista."}), 400

    sessao_auxiliar = curl_requests.Session(impersonate="chrome124")
    username = extrair_username(link_usuario, sessao_auxiliar)

    if not username:
        return jsonify({"erro": "Nao consegui identificar o usuario a partir desse link."}), 400

    roleta = LetterboxdRoulette(username)
    resultado = roleta.sortear(link_lista)

    status = 200 if "filme" in resultado or "erro" in resultado else 500
    return jsonify(resultado), status


if __name__ == "__main__":
    app.run(debug=True, port=5000)
