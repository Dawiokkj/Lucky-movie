const form = document.getElementById("sortear-form");
const usuarioInput = document.getElementById("link-usuario");
const linkInput = document.getElementById("link-lista");
const btn = document.getElementById("sortear-btn");
const hint = document.getElementById("stats-hint");

const placeholderCard = document.getElementById("placeholder-card");
const reel = document.getElementById("reel");
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

  document.getElementById("filme-sinopse").textContent = filme.sinopse || "Sinopse não disponível.";
  document.getElementById("filme-link").href = filme.url || "#";

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

form.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  const usuario = usuarioInput.value.trim();
  const link = linkInput.value.trim();
  if (!usuario || !link) return;

  if (salvarCheckbox && salvarCheckbox.checked) {
    localStorage.setItem("letterboxd_usuario", usuario);
    localStorage.setItem("letterboxd_lista", link);
    localStorage.setItem("letterboxd_salvar", "true");
  }

  esconderTudo();
  reel.hidden = false;
  btn.disabled = true;
  hint.textContent = "";

  try {
    const resposta = await fetch("/api/sortear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario, link }),
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
    hint.textContent = `${dados.total_disponiveis} de ${dados.total_lista} filmes da lista ainda não assistidos.`;
  } catch (erro) {
    mostrarErro("Não consegui falar com o servidor. Confira se o app está rodando e tente de novo.");
  } finally {
    btn.disabled = false;
    reel.hidden = true;
  }
});
