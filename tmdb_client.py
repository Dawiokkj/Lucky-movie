"""
Cliente para a API do The Movie Database (TMDB).

Usado pelo modo de sorteio "por filtros": busca filmes que batem com os
filtros escolhidos (genero, decada, nota minima - todos opcionais) e
sorteia um deles, pulando qualquer filme que ja esteja na lista de
assistidos do usuario no Letterboxd (repassada por quem chama).

Precisa da variavel de ambiente TMDB_API_KEY. Aceita tanto a "API Key"
(v3, string curta) quanto o "API Read Access Token" (v4, comeca com
"eyJ..."), pegos em https://www.themoviedb.org/settings/api
"""

import os
import re
import random
import unicodedata
from datetime import date

from curl_cffi import requests

BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w500"
TIMEOUT = 15
TOTAL_PAGINAS_MAXIMO = 500  # limite da propria API do TMDB
MAX_PAGINAS_TENTADAS = 6  # quantas paginas diferentes tentar ate achar um filme nao assistido


class TMDBError(Exception):
    """Erro de configuracao ou de comunicacao com a API do TMDB."""


def slugify(texto: str) -> str:
    """Aproxima o slug que o Letterboxd geraria pro mesmo titulo, pra
    poder cruzar um resultado do TMDB com a lista de assistidos."""
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto


class TMDBClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("TMDB_API_KEY", "")
        self.session = requests.Session(impersonate="chrome124")

    # ------------------------------------------------------------------
    # REQUISICAO BASE
    # ------------------------------------------------------------------
    def _get(self, caminho: str, params: dict | None = None) -> dict:
        if not self.api_key:
            raise TMDBError(
                "TMDB_API_KEY nao configurada no servidor. "
                "Defina a variavel de ambiente com sua chave da API do TMDB."
            )

        params = dict(params or {})
        headers = {}
        if self.api_key.startswith("eyJ"):  # Read Access Token (v4, JWT)
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:  # API Key (v3)
            params["api_key"] = self.api_key
        params.setdefault("language", "pt-BR")

        try:
            resp = self.session.get(
                f"{BASE_URL}{caminho}", params=params, headers=headers, timeout=TIMEOUT
            )
        except Exception as erro:
            raise TMDBError(f"Nao consegui falar com o TMDB agora ({type(erro).__name__}).") from erro
        if resp.status_code == 401:
            raise TMDBError("TMDB_API_KEY invalida ou expirada.")
        if resp.status_code != 200:
            raise TMDBError(f"TMDB respondeu {resp.status_code} em {caminho}.")
        return resp.json()

    # ------------------------------------------------------------------
    # GENEROS (para popular o filtro na interface)
    # ------------------------------------------------------------------
    def generos(self) -> list[dict]:
        dados = self._get("/genre/movie/list")
        return dados.get("genres", [])

    # ------------------------------------------------------------------
    # MONTAGEM DOS FILTROS -> PARAMETROS DO /discover/movie
    # ------------------------------------------------------------------
    def _montar_parametros(self, filtros: dict) -> dict:
        params = {
            "sort_by": "popularity.desc",
            "include_adult": "false",
            "vote_count.gte": 20,
        }

        generos = filtros.get("generos") or []
        if generos:
            # virgula = "E" (o filme precisa ter todos os generos marcados);
            # se fosse "OU" seria pipe (|). E o que foi pedido: selecionou
            # dois generos, quer filme que tenha os dois, nao um ou outro.
            params["with_genres"] = ",".join(str(g) for g in generos)

        decada = filtros.get("decada")
        if decada == "upcoming":
            params["primary_release_date.gte"] = date.today().isoformat()
            params["sort_by"] = "primary_release_date.asc"
            params.pop("vote_count.gte", None)  # filme que ainda nao estreou nao tem votos
        elif decada:
            inicio = int(decada)
            params["primary_release_date.gte"] = f"{inicio}-01-01"
            params["primary_release_date.lte"] = f"{inicio + 9}-12-31"

        nota_estrelas = filtros.get("nota_min_estrelas")
        if nota_estrelas:
            # Letterboxd usa escala de 0 a 5 estrelas; TMDB usa 0 a 10.
            params["vote_average.gte"] = float(nota_estrelas) * 2

        return params

    # ------------------------------------------------------------------
    # CRUZAMENTO COM OS FILMES JA ASSISTIDOS NO LETTERBOXD
    # ------------------------------------------------------------------
    @staticmethod
    def _ja_assistido(filme: dict, filmes_assistidos: set) -> bool:
        if not filmes_assistidos:
            return False
        # O Letterboxd indexa os filmes pelo titulo original/em ingles -
        # os slugs em filmes_assistidos vieram de la. O /discover/movie
        # (chamado em pt-BR) traz em "title" o titulo traduzido pro
        # portugues, que quase nunca gera o mesmo slug. Por isso aqui
        # precisa testar original_title PRIMEIRO (e so cair pro "title"
        # traduzido se o filme nao tiver original_title por algum motivo),
        # senao um filme ja assistido passa batido nesse cruzamento - foi
        # exatamente esse o bug reportado ("Minions & Monstros"/"Minions &
        # Monsters" sendo sorteado de novo).
        titulo = filme.get("original_title") or filme.get("title") or ""
        titulo_traduzido = filme.get("title") or ""
        ano = (filme.get("release_date") or "")[:4]

        candidatos = set()
        for base in {slugify(titulo), slugify(titulo_traduzido)}:
            if not base:
                continue
            candidatos.add(base)
            if ano:
                candidatos.add(f"{base}-{ano}")

        return bool(candidatos & filmes_assistidos)

    # ------------------------------------------------------------------
    # SORTEIO POR FILTROS
    # ------------------------------------------------------------------
    def sortear(self, filtros: dict | None = None, filmes_assistidos: set | None = None) -> dict:
        """Sorteia um filme do catalogo do TMDB que bata com os filtros
        informados (todos opcionais) e que nao esteja em
        filmes_assistidos (slugs no estilo Letterboxd)."""
        filtros = filtros or {}
        filmes_assistidos = filmes_assistidos or set()
        params = self._montar_parametros(filtros)

        primeira_pagina = self._get("/discover/movie", {**params, "page": 1})
        total_paginas = min(primeira_pagina.get("total_pages", 0), TOTAL_PAGINAS_MAXIMO)
        total_resultados = primeira_pagina.get("total_results", 0)

        if total_paginas == 0 or not primeira_pagina.get("results"):
            return {"erro": "Nenhum filme encontrado com esses filtros. Tente afrouxar algum deles."}

        paginas_tentadas = set()
        tentativas = min(MAX_PAGINAS_TENTADAS, total_paginas)

        for indice in range(tentativas):
            if indice == 0:
                pagina_num = 1
                dados_pagina = primeira_pagina
            else:
                paginas_restantes = [p for p in range(1, total_paginas + 1) if p not in paginas_tentadas]
                if not paginas_restantes:
                    break
                pagina_num = random.choice(paginas_restantes)
                dados_pagina = self._get("/discover/movie", {**params, "page": pagina_num})

            paginas_tentadas.add(pagina_num)
            resultados = dados_pagina.get("results") or []
            disponiveis = [f for f in resultados if not self._ja_assistido(f, filmes_assistidos)]

            if disponiveis:
                escolhido = random.choice(disponiveis)
                detalhes = self.obter_detalhes_filme(escolhido["id"])
                return {"filme": detalhes, "total_disponiveis": total_resultados}

        return {
            "erro": (
                "Nao encontrei nenhum filme com esses filtros que voce ainda nao tenha "
                "assistido. Tente afrouxar algum filtro."
            )
        }

    # ------------------------------------------------------------------
    # DETALHES DO FILME SORTEADO (capa, titulo, ano, diretor, sinopse)
    # ------------------------------------------------------------------
    @staticmethod
    def _titulo_para_busca_letterboxd(dados: dict) -> str:
        """O Letterboxd indexa os filmes pelo titulo original (quando a
        producao e em ingles) ou pelo titulo em ingles (quando nao e) -
        nunca pelo titulo traduzido pro portugues, que e so o que a
        resposta em pt-BR da API do TMDB traz em 'title'. Busca o titulo
        em ingles nas traducoes do filme; se nao achar, cai pro titulo
        original (que ja e o titulo em ingles quando a producao e dos
        EUA/Reino Unido etc.)."""
        traducoes = (dados.get("translations") or {}).get("translations") or []
        candidatos_en = [t for t in traducoes if t.get("iso_639_1") == "en"]
        preferido = next((t for t in candidatos_en if t.get("iso_3166_1") == "US"), None)
        preferido = preferido or (candidatos_en[0] if candidatos_en else None)
        titulo_en = (preferido or {}).get("data", {}).get("title")

        return titulo_en or dados.get("original_title") or dados.get("title") or ""

    def obter_detalhes_filme(self, tmdb_id: int) -> dict:
        dados = self._get(f"/movie/{tmdb_id}", {"append_to_response": "credits,translations"})

        diretor = next(
            (
                pessoa.get("name", "")
                for pessoa in dados.get("credits", {}).get("crew", [])
                if pessoa.get("job") == "Director"
            ),
            "",
        )
        poster_path = dados.get("poster_path")
        titulo = dados.get("title") or dados.get("original_title") or ""
        titulo_busca = self._titulo_para_busca_letterboxd(dados)

        return {
            "titulo": titulo,
            # Titulo original/em ingles - usado pra linkar e pra adivinhar
            # o slug do Letterboxd (que indexa pelo titulo original/en,
            # nunca pelo traduzido pro portugues).
            "titulo_original": titulo_busca,
            "ano": (dados.get("release_date") or "")[:4],
            "diretor": diretor,
            "sinopse": dados.get("overview", ""),
            "poster": f"{IMG_BASE}{poster_path}" if poster_path else "",
            # Esse filme veio do catalogo do TMDB, nao foi raspado do
            # Letterboxd, entao nao sabemos a URL exata (nem garantida) da
            # pagina do filme la - o "slug" e so uma adivinhacao. Por isso
            # o botao "ver no Letterboxd" fica reservado so para os filmes
            # sorteados a partir de uma lista (que tem o slug real); aqui
            # deixamos url vazia de proposito, e o frontend esconde o botao
            # quando nao ha url.
            "url": "",
            # Essa, sim, e sempre uma URL exata - e a propria pagina do
            # filme no TMDB, pelo id que a gente ja tem.
            "url_tmdb": f"https://www.themoviedb.org/movie/{tmdb_id}",
        }
