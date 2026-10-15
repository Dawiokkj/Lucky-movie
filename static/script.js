// Path de uma estrela de 5 pontas, geometricamente simetrica em torno de
// x=12 (viewBox 0 0 24 24) - usada tanto no filtro de nota minima quanto
// na exibicao da nota do Letterboxd. Evita o glifo unicode "★", que nao e
// simetrico dentro do proprio box e por isso nunca cortava a meia estrela
// exatamente no meio.
const SVG_ESTRELA_PATH = "M 12 2 L 14.35 8.76 L 21.51 8.91 L 15.8 13.24 L 17.88 20.09 L 12 16 L 6.12 20.09 L 8.2 13.24 L 2.49 8.91 L 9.65 8.76 Z";

function criarEstrelaSVG(classe) {
  const estrela = document.createElement("span");
  estrela.className = "star";
  estrela.innerHTML = `
    <svg class="star-bg" viewBox="0 0 24 24"><path d="${SVG_ESTRELA_PATH}"></path></svg>
    <span class="star-fg-wrap"><svg class="star-fg" viewBox="0 0 24 24"><path d="${SVG_ESTRELA_PATH}"></path></svg></span>
  `;
  if (classe) estrela.classList.add(classe);
  return estrela;
}

function preencherEstrela(estrela, fracao) {
  const largura = Math.max(0, Math.min(1, fracao)) * 100;
  estrela.querySelector(".star-fg-wrap").style.width = `${largura}%`;
}

// Renderiza uma fileira de 5 estrelas somente-leitura (nao clicaveis) com
// a nota preenchida fracionalmente - usada para mostrar a nota do
// Letterboxd (escala 0-5) junto do filme sorteado.
function renderEstrelasLeitura(container, nota) {
  if (!container) return;
  container.innerHTML = "";
  if (nota === null || nota === undefined) {
    container.hidden = true;
    return;
  }
  container.hidden = false;
  for (let indice = 1; indice <= 5; indice++) {
    const estrela = criarEstrelaSVG();
    const fracao = Math.max(0, Math.min(1, nota - (indice - 1)));
    preencherEstrela(estrela, fracao);
    container.appendChild(estrela);
  }
  const valor = document.createElement("span");
  valor.className = "star-value";
  valor.textContent = nota.toFixed(1);
  container.appendChild(valor);
}

const form = document.getElementById("sortear-form");
const usuarioInput = document.getElementById("link-usuario");
const linkInput = document.getElementById("link-lista");
const btn = document.getElementById("sortear-btn");
const hint = document.getElementById("stats-hint");

const placeholderCard = document.getElementById("placeholder-card");
const reel = document.getElementById("reel");
const reelSubtitle = document.getElementById("reel-subtitle");
const alertBox = document.getElementById("alert");
const posterCard = document.getElementById("poster-card");
const salvarCheckbox = document.getElementById("salvar-dados");

// Carregar dados do localStorage se habilitado
if (salvarCheckbox) {
  const usuarioSalvo = localStorage.getItem("letterboxd_usuario");
  const listaSalva = localStorage.getItem("letterboxd_lista");
  const deveSalvar = localStorage.getItem("letterboxd_salvar") === "true";

  if (deveSalvar) {
    salvarCheckbox.checked = true;
    if (usuarioSalvo) usuarioInput.value = usuarioSalvo;
    if (listaSalva) linkInput.value = listaSalva;
  }

  salvarCheckbox.addEventListener("change", () => {
    if (!salvarCheckbox.checked) {
      localStorage.removeItem("letterboxd_usuario");
      localStorage.removeItem("letterboxd_lista");
      localStorage.setItem("letterboxd_salvar", "false");
    } else {
      localStorage.setItem("letterboxd_salvar", "true");
      if (usuarioInput.value.trim()) localStorage.setItem("letterboxd_usuario", usuarioInput.value.trim());
      if (linkInput.value.trim()) localStorage.setItem("letterboxd_lista", linkInput.value.trim());
    }
  });
}

function esconderTudo() {
  placeholderCard.hidden = true;
  reel.hidden = true;
  alertBox.hidden = true;
  posterCard.hidden = true;
}

function mostrarErro(mensagem) {
  esconderTudo();
  alertBox.textContent = mensagem;
  alertBox.hidden = false;
}

function mostrarResultado(filme) {
  esconderTudo();

  document.getElementById("poster-img").src = filme.poster || "";
  document.getElementById("poster-img").alt = filme.titulo || "Capa do filme";
  document.getElementById("filme-titulo").textContent = filme.titulo || "(sem título)";
  document.getElementById("filme-ano").textContent = filme.ano ? `(${filme.ano})` : "";

  const diretorWrapper = document.getElementById("filme-diretor-wrapper");
  if (filme.diretor && filme.diretor.toLowerCase() !== "desconhecido") {
    document.getElementById("filme-diretor").textContent = filme.diretor;
    if (diretorWrapper) diretorWrapper.hidden = false;
  } else {
    document.getElementById("filme-diretor").textContent = "";
    if (diretorWrapper) diretorWrapper.hidden = true;
  }

  renderEstrelasLeitura(
    document.getElementById("filme-nota"),
    typeof filme.nota_letterboxd === "number" ? filme.nota_letterboxd : null
  );

  document.getElementById("filme-sinopse").textContent = filme.sinopse || "Sinopse não disponível.";

  // O botao "ver no Letterboxd" so existe para filmes sorteados a partir
  // de uma lista (slug real, raspado do Letterboxd). Filmes sorteados via
  // filtros do TMDB nao tem url (ver tmdb_client.py), entao o botao fica
  // escondido pra nao linkar pra uma pagina adivinhada/errada.
  const linkWrapper = document.getElementById("filme-link-wrapper");
  if (filme.url) {
    document.getElementById("filme-link").href = filme.url;
    if (linkWrapper) linkWrapper.hidden = false;
  } else if (linkWrapper) {
    linkWrapper.hidden = true;
  }

  // O botao "ver no The Movie Database" e o oposto: so existe para filmes
  // sorteados via filtros do TMDB (os unicos que tem url_tmdb), pra quem
  // quiser mais informacoes sobre o filme direto na fonte.
  const linkTmdbWrapper = document.getElementById("filme-link-tmdb-wrapper");
  if (filme.url_tmdb) {
    document.getElementById("filme-link-tmdb").href = filme.url_tmdb;
    if (linkTmdbWrapper) linkTmdbWrapper.hidden = false;
  } else if (linkTmdbWrapper) {
    linkTmdbWrapper.hidden = true;
  }

  // recria as divs de cortina para reiniciar a animacao a cada sorteio
  const antigasCortinas = posterCard.querySelectorAll(".curtain");
  antigasCortinas.forEach((c) => c.remove());

  const esquerda = document.createElement("div");
  esquerda.className = "curtain curtain--left";
  esquerda.setAttribute("aria-hidden", "true");

  const direita = document.createElement("div");
  direita.className = "curtain curtain--right";
  direita.setAttribute("aria-hidden", "true");

  posterCard.prepend(direita);
  posterCard.prepend(esquerda);

  posterCard.hidden = false;
}

// ---------- Gêneros do TMDB (dropdown estilo Netflix, seleção múltipla = "E", não "OU") ----------
const tmdbGenerosBox = document.getElementById("tmdb-generos");
const tmdbGenerosDropdown = document.getElementById("tmdb-generos-dropdown");
const tmdbGenerosBtn = document.getElementById("tmdb-generos-btn");
const tmdbGenerosLabel = document.getElementById("tmdb-generos-label");

function atualizarLabelGeneros() {
  if (!tmdbGenerosBox || !tmdbGenerosLabel) return;
  const selecionados = Array.from(tmdbGenerosBox.querySelectorAll("input:checked"));
  if (selecionados.length === 0) {
    tmdbGenerosLabel.textContent = "Qualquer gênero";
  } else if (selecionados.length === 1) {
    tmdbGenerosLabel.textContent = selecionados[0].closest(".genero-item").querySelector("span").textContent;
  } else {
    tmdbGenerosLabel.textContent = `${selecionados.length} gêneros selecionados`;
  }
}

function abrirFecharDropdownGeneros(aberto) {
  if (!tmdbGenerosBox || !tmdbGenerosBtn) return;
  tmdbGenerosBox.hidden = !aberto;
  tmdbGenerosBtn.setAttribute("aria-expanded", String(aberto));
}

if (tmdbGenerosBtn) {
  tmdbGenerosBtn.addEventListener("click", () => {
    abrirFecharDropdownGeneros(tmdbGenerosBox.hidden);
  });
}

// fecha o dropdown ao clicar fora dele
document.addEventListener("click", (evento) => {
  if (tmdbGenerosDropdown && !tmdbGenerosDropdown.contains(evento.target)) {
    abrirFecharDropdownGeneros(false);
  }
});

async function carregarGeneros() {
  if (!tmdbGenerosBox) return;
  try {
    const resposta = await fetch("/api/generos");
    const dados = await resposta.json();

    if (dados.erro) {
      tmdbGenerosBox.textContent = dados.erro;
      return;
    }

    tmdbGenerosBox.innerHTML = "";
    (dados.generos || []).forEach((genero) => {
      const label = document.createElement("label");
      label.className = "genero-item";
      label.setAttribute("role", "option");
      label.innerHTML = `<input type="checkbox" value="${genero.id}"><span>${genero.name}</span>`;
      tmdbGenerosBox.appendChild(label);
    });

    tmdbGenerosBox.addEventListener("change", atualizarLabelGeneros);
    atualizarLabelGeneros();
  } catch (erro) {
    tmdbGenerosBox.textContent = "Não consegui carregar os gêneros do TMDB.";
  }
}
carregarGeneros();

// ---------- Nota mínima em estrelas (meia estrela, igual ao Letterboxd) ----------
const estrelasBox = document.getElementById("tmdb-estrelas");
let notaEstrelas = 0; // 0 = sem filtro de nota

function renderEstrelas(valorPreview) {
  if (!estrelasBox) return;
  const valor = valorPreview !== undefined ? valorPreview : notaEstrelas;

  estrelasBox.querySelectorAll(".star").forEach((estrela) => {
    const indice = Number(estrela.dataset.indice);
    let fracao = 0;
    if (valor >= indice) fracao = 1;
    else if (valor >= indice - 0.5) fracao = 0.5;
    preencherEstrela(estrela, fracao);
  });

  const label = document.getElementById("tmdb-estrelas-label");
  if (label) {
    label.textContent = notaEstrelas > 0 ? `${notaEstrelas.toFixed(1)} ou mais` : "qualquer nota";
  }
}

function calcularValorClique(estrela, indice, evento) {
  // Usa a largura real do SVG da estrela (nao do <span> que a envolve,
  // que pode ter folga/whitespace extra) para que o corte da metade bata
  // exatamente no meio do desenho.
  const svg = estrela.querySelector(".star-bg");
  const retangulo = svg.getBoundingClientRect();
  const fracao = (evento.clientX - retangulo.left) / retangulo.width;
  return fracao < 0.5 ? indice - 0.5 : indice;
}

if (estrelasBox) {
  for (let indice = 1; indice <= 5; indice++) {
    const estrela = criarEstrelaSVG();
    estrela.dataset.indice = String(indice);

    estrela.addEventListener("mousemove", (evento) => {
      renderEstrelas(calcularValorClique(estrela, indice, evento));
    });
    estrela.addEventListener("mouseleave", () => renderEstrelas());
    estrela.addEventListener("click", (evento) => {
      const valorClicado = calcularValorClique(estrela, indice, evento);
      // clicar na mesma nota de novo limpa o filtro
      notaEstrelas = notaEstrelas === valorClicado ? 0 : valorClicado;
      renderEstrelas();
    });

    estrelasBox.appendChild(estrela);
  }

  const label = document.createElement("span");
  label.id = "tmdb-estrelas-label";
  label.className = "star-label";
  estrelasBox.appendChild(label);

  renderEstrelas();
}

// ---------- Envio do formulário ----------
form.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  const usuario = usuarioInput.value.trim();
  const link = linkInput.value.trim();
  if (!usuario) return;

  if (salvarCheckbox && salvarCheckbox.checked) {
    localStorage.setItem("letterboxd_usuario", usuario);
    localStorage.setItem("letterboxd_lista", link);
    localStorage.setItem("letterboxd_salvar", "true");
  }

  const generosSelecionados = tmdbGenerosBox
    ? Array.from(tmdbGenerosBox.querySelectorAll("input:checked")).map((el) => el.value)
    : [];
  const decada = document.getElementById("tmdb-decada")
    ? document.getElementById("tmdb-decada").value
    : "";

  const usaLista = Boolean(link);

  esconderTudo();
  reelSubtitle.textContent = usaLista
    ? "Cruzando a lista do Letterboxd com seus filmes assistidos..."
    : "Buscando um filme que bata com seus filtros (e que você ainda não viu)...";
  reel.hidden = false;
  btn.disabled = true;
  hint.textContent = "";

  try {
    const resposta = await fetch("/api/sortear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        usuario,
        link,
        generos: generosSelecionados,
        decada: decada || null,
        nota_min_estrelas: notaEstrelas || null,
      }),
    });

    const dados = await resposta.json();

    if (dados.erro) {
      mostrarErro(dados.erro);
      if (dados.total_lista) {
        hint.textContent = `${dados.total_lista} filmes na lista.`;
      }
      return;
    }

    mostrarResultado(dados.filme);
    if (usaLista) {
      hint.textContent = `${dados.total_disponiveis} de ${dados.total_lista} filmes da lista ainda não assistidos.`;
    } else {
      hint.textContent = dados.total_disponiveis
        ? `${dados.total_disponiveis} filmes encontrados com esses filtros.`
        : "";
    }
  } catch (erro) {
    mostrarErro("Não consegui falar com o servidor. Confira se o app está rodando e tente de novo.");
  } finally {
    btn.disabled = false;
    reel.hidden = true;
  }
});
