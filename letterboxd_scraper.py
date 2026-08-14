"""
Logica de busca no Letterboxd, reutilizada pelo app web (app.py).

Le os filmes de uma lista publica do Letterboxd, cruza com os filmes que
o usuario informado ja assistiu, e sorteia um filme entre os restantes -
retornando capa, titulo, ano, diretor e sinopse.

Nao precisa de login: usa o nome/link de usuario informado pela pessoa e
le as paginas publicas do perfil. So funciona se o perfil estiver com
visibilidade padrao (publica).
"""

import re
import time
import random
from urllib.parse import urlparse

from curl_cffi import requests
from bs4 import BeautifulSoup

BASE_URL = "https://letterboxd.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://letterboxd.com/",
}
PAUSA_ENTRE_PAGINAS = 0.8  # segundos, para nao martelar o servidor
TIMEOUT = 15  # segundos de timeout por requisicao


def extrair_username(entrada_usuario: str, session) -> str:
    """Aceita tanto um nome de usuario puro ('Dawikkj') quanto um link
    completo do perfil ('https://letterboxd.com/Dawikkj/') e devolve o
    username. Resolve redirecionamentos, entao tambem funciona com
    links curtos, se algum dia existirem para perfis."""
    entrada_usuario = entrada_usuario.strip()

    if not entrada_usuario.lower().startswith("http"):
        # username puro, sem link - so limpa barras acidentais
        return entrada_usuario.strip("/")

    resp = session.get(entrada_usuario, allow_redirects=True, timeout=TIMEOUT)
    caminho = urlparse(resp.url).path
    partes = [p for p in caminho.split("/") if p]
    return partes[0] if partes else ""


class LetterboxdRoulette:
    def __init__(self, username: str):
        self.session = requests.Session(impersonate="chrome124")
        self.session.headers.update(HEADERS)
        self.username = username

    # ------------------------------------------------------------------
    # VALIDACAO DO USUARIO
    # ------------------------------------------------------------------
    def usuario_existe(self) -> bool:
        resp = self.session.get(f"{BASE_URL}/{self.username}/", timeout=TIMEOUT)
        if resp.status_code == 403:
            return False
        return resp.status_code == 200

    # ------------------------------------------------------------------
    # RESOLUCAO DE LINK E EXTRACAO DE FILMES
    # ------------------------------------------------------------------
    def resolver_link_lista(self, link_lista: str) -> str:
        resp = self.session.get(link_lista, allow_redirects=True, timeout=TIMEOUT)
        parsed = urlparse(resp.url)
        caminho = parsed.path
        if not caminho.endswith("/"):
            caminho += "/"
        return caminho

    def _extrair_slugs_da_pagina(self, html: str):
        # Procura o padrao de URL "/film/<slug>/" em qualquer lugar do
        # HTML - mais resistente a mudancas de layout do que depender de
        # um atributo especifico.
        candidatos = re.findall(r"/film/([a-z0-9][a-z0-9\-]*)/", html)
        ignorar_sufixos = {
            "reviews", "likes", "lists", "crew", "genres", "nanogenres",
            "similar", "activity", "ratings", "fans",
        }
        return {slug for slug in candidatos if slug not in ignorar_sufixos}

    def obter_todos_slugs(self, caminho_base: str):
        todos_slugs = set()
        pagina = 1
        while True:
            url = (
                f"{BASE_URL}{caminho_base}"
                if pagina == 1
                else f"{BASE_URL}{caminho_base}page/{pagina}/"
            )
            resp = self.session.get(url, timeout=TIMEOUT)
            if resp.status_code != 200:
                break
            slugs_pagina = self._extrair_slugs_da_pagina(resp.text)
            if not slugs_pagina:
                break
            todos_slugs.update(slugs_pagina)
            pagina += 1
            time.sleep(PAUSA_ENTRE_PAGINAS)
        return todos_slugs

    def obter_filmes_assistidos(self):
        caminho = f"/{self.username}/films/"
        return self.obter_todos_slugs(caminho)

    def obter_filmes_da_lista(self, link_lista: str):
        caminho = self.resolver_link_lista(link_lista)
        return self.obter_todos_slugs(caminho)

    # ------------------------------------------------------------------
    # DETALHES DO FILME SORTEADO (capa, titulo, ano, diretor, sinopse)
    # ------------------------------------------------------------------
    def obter_detalhes_filme(self, slug: str):
        resp = self.session.get(f"{BASE_URL}/film/{slug}/", timeout=TIMEOUT)
        if resp.status_code != 200:
            return {
                "slug": slug,
                "titulo": slug,
                "ano": "",
                "diretor": "",
                "sinopse": "",
                "poster": "",
                "url": f"{BASE_URL}/film/{slug}/",
            }

        soup = BeautifulSoup(resp.text, "html.parser")

        def meta(prop=None, name=None):
            tag = (
                soup.find("meta", attrs={"property": prop})
                if prop
                else soup.find("meta", attrs={"name": name})
            )
            return tag.get("content", "").strip() if tag and tag.get("content") else ""

        titulo_ano = meta(prop="og:title")  # ex: "Parasite (2019)"
        poster = meta(prop="og:image")
        diretor = meta(name="twitter:data1")  # rotulado "Directed by"
        sinopse = meta(prop="og:description")

        m = re.match(r"^(.*)\s\((\d{4})\)\s*$", titulo_ano)
        if m:
            titulo, ano = m.group(1).strip(), m.group(2)
        else:
            titulo, ano = titulo_ano, ""

        return {
            "slug": slug,
            "titulo": titulo,
            "ano": ano,
            "diretor": diretor,
            "sinopse": sinopse,
            "poster": poster,
            "url": f"{BASE_URL}/film/{slug}/",
        }

    # ------------------------------------------------------------------
    # SORTEIO COMPLETO
    # ------------------------------------------------------------------
    def sortear(self, link_lista: str):
        """Retorna um dict com o resultado do sorteio ou um dict de erro."""
        if not self.usuario_existe():
            return {"erro": f"Usuario '{self.username}' nao encontrado (ou perfil privado/bloqueio temporario)."}

        filmes_lista = self.obter_filmes_da_lista(link_lista)
        if not filmes_lista:
            return {"erro": "Nao encontrei filmes nesse link de lista. Confira se o link esta correto."}

        filmes_assistidos = self.obter_filmes_assistidos()
        disponiveis = list(filmes_lista - filmes_assistidos)

        if not disponiveis:
            return {
                "erro": "Voce ja assistiu a todos os filmes dessa lista!",
                "total_lista": len(filmes_lista),
                "total_assistidos_na_lista": len(filmes_lista),
            }

        escolhido = random.choice(disponiveis)
        detalhes = self.obter_detalhes_filme(escolhido)

        return {
            "filme": detalhes,
            "total_lista": len(filmes_lista),
            "total_disponiveis": len(disponiveis),
        }
