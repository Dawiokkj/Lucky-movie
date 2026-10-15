"""
App web da Roleta de Filmes.

Rode com:
    python app.py

Depois abra http://127.0.0.1:5000 no navegador.

Dependencias:
    pip install flask curl_cffi beautifulsoup4 python-dotenv

Tem um unico formulario com dois jeitos de sortear:
  - Se o link da lista do Letterboxd for informado, sorteia dessa lista
    (comportamento original).
  - Se o link da lista ficar em branco, sorteia direto do catalogo do
    TMDB usando os filtros escolhidos (genero, decada, nota minima) -
    mas sempre cruzando com os filmes que o usuario ja assistiu no
    Letterboxd, pra nunca repetir um filme.

Para o sorteio por filtros (TMDB), defina sua chave da API do TMDB
(gratuita em https://www.themoviedb.org/settings/api) no arquivo .env
na raiz do projeto (veja .env.example) - nao precisa mais setar a
variavel de ambiente manualmente toda vez que for rodar o programa.
"""

from dotenv import load_dotenv

# Le o arquivo .env (se existir) e poe o que tiver la nas variaveis de
# ambiente do processo - assim TMDB_API_KEY fica disponivel pro
# TMDBClient() sem precisar setar na mao toda vez que for rodar o app.
load_dotenv()

from flask import Flask, render_template, request, jsonify

from letterboxd_scraper import LetterboxdRoulette, extrair_username
from tmdb_client import TMDBClient, TMDBError, slugify
from curl_cffi import requests as curl_requests

app = Flask(__name__)
tmdb = TMDBClient()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generos")
def generos():
    """Lista de generos do TMDB, para popular os filtros na interface."""
    try:
        return jsonify({"generos": tmdb.generos()})
    except TMDBError as erro:
        return jsonify({"erro": str(erro)}), 500


@app.route("/api/sortear", methods=["POST"])
def sortear():
    data = request.get_json(silent=True) or {}
    link_usuario = (data.get("usuario") or "").strip()
    link_lista = (data.get("link") or "").strip()

    if not link_usuario:
        return jsonify({"erro": "Informe o link (ou nome) do seu perfil no Letterboxd."}), 400

    sessao_auxiliar = curl_requests.Session(impersonate="chrome124")
    username = extrair_username(link_usuario, sessao_auxiliar)
    if not username:
        return jsonify({"erro": "Nao consegui identificar o usuario a partir desse link."}), 400

    roleta = LetterboxdRoulette(username)

    # ---- Modo 1: sorteio a partir da lista do Letterboxd (link informado) ----
    if link_lista:
        resultado = roleta.sortear(link_lista)
        status = 200 if "filme" in resultado or "erro" in resultado else 500
        return jsonify(resultado), status

    # ---- Modo 2: sorteio por filtros do TMDB (sem link de lista) ----
    if not roleta.usuario_existe():
        return jsonify({"erro": roleta.mensagem_usuario_indisponivel()}), 400

    filmes_assistidos = roleta.obter_filmes_assistidos()

    filtros = {
        "generos": data.get("generos") or [],
        "decada": (data.get("decada") or "").strip() or None,
        "nota_min_estrelas": data.get("nota_min_estrelas") or None,
    }

    try:
        resultado = tmdb.sortear(filtros, filmes_assistidos=filmes_assistidos)
    except TMDBError as erro:
        return jsonify({"erro": str(erro)}), 500

    # Filme veio do TMDB, entao a nota do Letterboxd nao veio junto -
    # tenta adivinhar o slug a partir do titulo original/em ingles (o
    # Letterboxd indexa por esse, nunca pelo traduzido pro portugues), e
    # titulo+ano como alternativa, e buscar so a nota na pagina do
    # Letterboxd. Se nao achar, segue sem nota (o frontend simplesmente
    # nao mostra essa parte).
    if "filme" in resultado:
        filme = resultado["filme"]
        titulo_para_slug = filme.get("titulo_original") or filme.get("titulo", "")
        slug_base = slugify(titulo_para_slug)
        candidatos_slug = [slug_base]
        if filme.get("ano"):
            candidatos_slug.append(f"{slug_base}-{filme['ano']}")

        nota = None
        for slug_candidato in candidatos_slug:
            nota = roleta.obter_nota_por_slug(slug_candidato)
            if nota is not None:
                break
        filme["nota_letterboxd"] = nota

    status = 200 if "filme" in resultado else 400
    return jsonify(resultado), status


if __name__ == "__main__":
    # Rodando local: debug ligado. Em producao (Render etc.) quem sobe o app
    # e o gunicorn (veja Procfile), entao este bloco nem e executado.
    app.run(debug=True, port=5000)
