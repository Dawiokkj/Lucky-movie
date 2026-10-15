# Lucky-movie
App web da Roleta de Filmes.

Tem um unico formulario:

- **Com link de lista do Letterboxd**: sorteia um filme dessa lista, cruzando
  com os filmes que voce ja assistiu (comportamento original).
- **Sem link de lista** (campo em branco): sorteia direto do catalogo do
  The Movie Database (TMDB), usando os filtros escolhidos (genero, decada,
  nota minima - todos opcionais), mas sempre cruzando com os filmes que
  voce ja assistiu no Letterboxd, pra nunca sortear um filme repetido.
  Selecionar mais de um genero busca filmes que tenham todos eles (E),
  nao apenas um ou outro (OU).

Rode com:
   1. python app.py
   2. Depois abra http://127.0.0.1:5000 no navegador.

> Dependencias:
>>  pip install flask curl_cffi beautifulsoup4 python-dotenv

> Para o sorteio por filtros (TMDB), precisa de uma chave gratuita da API,
> obtida em https://www.themoviedb.org/settings/api (funciona tanto com a
> "API Key" v3 quanto com o "API Read Access Token" v4).
>
> Deixe a chave salva de forma definitiva no projeto, num arquivo `.env`
> na raiz (ja incluso no `.gitignore`, entao nunca vai parar no GitHub):
>>  TMDB_API_KEY=sua_chave_aqui
>
> Existe um `.env.example` de modelo - e so copiar pra `.env` e colar a
> chave. Com o `.env` configurado, nao precisa mais setar nenhuma
> variavel de ambiente na mao: e so rodar `python app.py` normalmente,
> sempre.
