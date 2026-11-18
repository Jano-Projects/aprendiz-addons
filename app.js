/*
 * Lógica da loja de addons (JavaScript puro).
 *
 *   1. Utilidades (DOM, escape de HTML, formatos)
 *   2. Tema claro/escuro
 *   3. Carregar o catálogo
 *   4. Filtros: busca (sem acentos), categoria, ordenação, link compartilhável
 *   5. Cartões
 *
 * Todo texto vindo do catálogo é escapado antes de ir para a página.
 */
(function () {
  "use strict";

  // ============================================================ 1. UTILIDADES
  const $ = (s, r) => (r || document).querySelector(s);
  const icone = (nome) => `<svg class="ic" aria-hidden="true"><use href="#i-${nome}"/></svg>`;

  function esc(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  /** "Atalhos do Windows" → "atalhos do windows" (sem acento, minúsculas), para a busca. */
  function normalizar(texto) {
    return String(texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function tamanho(bytes) {
    return bytes < 1024 ? `${bytes} B` : bytes < 1048576
      ? `${(bytes / 1024).toFixed(1).replace(".", ",")} KB`
      : `${(bytes / 1048576).toFixed(1).replace(".", ",")} MB`;
  }

  function data(iso) {
    const [a, m, d] = String(iso).split("-");
    return d ? `${d}/${m}/${a}` : iso;
  }

  function avisar(texto) {
    document.querySelectorAll(".aviso-flutuante").forEach((e) => e.remove());
    const el = document.createElement("div");
    el.className = "aviso-flutuante";
    el.textContent = texto;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2400);
  }

  /**
   * Destaca os termos buscados. As posições são encontradas no texto ORIGINAL
   * (sem acentos para comparar) e cada pedaço é escapado separadamente, então o
   * destaque nunca quebra o HTML.
   */
  function destacar(texto, termos) {
    texto = String(texto ?? "");
    const base = normalizar(texto);
    if (!termos.length || base.length !== texto.length) return esc(texto);
    const marcado = new Array(texto.length).fill(false);
    termos.forEach((t) => {
      let i = base.indexOf(t);
      while (t && i !== -1) { marcado.fill(true, i, i + t.length); i = base.indexOf(t, i + t.length); }
    });
    let html = "", dentro = false;
    for (let i = 0; i < texto.length; i++) {
      if (marcado[i] !== dentro) { html += marcado[i] ? "<mark>" : "</mark>"; dentro = marcado[i]; }
      html += esc(texto[i]);
    }
    return html + (dentro ? "</mark>" : "");
  }

  // ============================================================ 2. TEMA
  function preferido() {
    try { return localStorage.getItem("loja.tema"); } catch (e) { return null; }
  }
  function aplicarTema(tema) {
    document.documentElement.dataset.tema = tema;
    $("#btn-tema").innerHTML = icone(tema === "escuro" ? "sol" : "lua");
  }
  const escuro = window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches;
  aplicarTema(preferido() || (escuro ? "escuro" : "claro"));
  $("#btn-tema").addEventListener("click", () => {
    const novo = document.documentElement.dataset.tema === "escuro" ? "claro" : "escuro";
    aplicarTema(novo);
    try { localStorage.setItem("loja.tema", novo); } catch (e) { /* ignora */ }
  });

  // ============================================================ 3. CATÁLOGO
  const estado = { addons: [], categoria: "Todas" };

  async function carregar() {
    try {
      const r = await fetch("catalogo.json", { cache: "no-cache" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const catalogo = await r.json();
      estado.addons = catalogo.addons || [];
      if (catalogo.gerado_em) {
        $("#gerado-em").textContent = "Catálogo atualizado em " + new Date(catalogo.gerado_em).toLocaleDateString("pt-BR");
      }
    } catch (erro) {
      $("#resumo").textContent = "Não foi possível carregar o catálogo de addons.";
      return;
    }
    lerEndereco();
    montarCategorias();
    renderizar();
  }

  // ============================================================ 4. FILTROS
  /** ?busca=linux&categoria=Tecnologia → permite compartilhar uma busca. */
  function lerEndereco() {
    const p = new URLSearchParams(location.search);
    $("#busca").value = p.get("busca") || "";
    estado.categoria = p.get("categoria") || "Todas";
    if (["nome", "recentes", "tamanho"].includes(p.get("ordem"))) $("#ordem").value = p.get("ordem");
  }

  function gravarEndereco() {
    const p = new URLSearchParams();
    if ($("#busca").value.trim()) p.set("busca", $("#busca").value.trim());
    if (estado.categoria !== "Todas") p.set("categoria", estado.categoria);
    if ($("#ordem").value !== "nome") p.set("ordem", $("#ordem").value);
    const q = p.toString();
    history.replaceState(null, "", q ? "?" + q : location.pathname);
  }

  function montarCategorias() {
    const contagem = {};
    estado.addons.forEach((a) => { contagem[a.categoria] = (contagem[a.categoria] || 0) + 1; });
    const nomes = ["Todas", ...Object.keys(contagem).sort((a, b) => a.localeCompare(b, "pt-BR"))];
    if (!nomes.includes(estado.categoria)) estado.categoria = "Todas";
    $("#categorias").innerHTML = nomes.map((c) => `
      <button class="chip ${c === estado.categoria ? "ativo" : ""}" data-categoria="${esc(c)}">
        ${esc(c)}<small>${c === "Todas" ? estado.addons.length : contagem[c]}</small></button>`).join("");
    $("#categorias").querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
      estado.categoria = b.dataset.categoria;
      montarCategorias();
      renderizar();
    }));
  }

  function filtrar() {
    const termos = normalizar($("#busca").value).split(/\s+/).filter(Boolean);
    let lista = estado.addons.filter((a) => {
      if (estado.categoria !== "Todas" && a.categoria !== estado.categoria) return false;
      if (!termos.length) return true;
      const texto = normalizar([a.id, a.nome, a.descricao, a.autor, a.categoria, ...(a.etiquetas || []),
        ...(a.amostra || []).map((x) => `${x.pergunta || ""} ${x.conteudo}`), ...(a.palavras || []),
        ...(a.traducoes || [])].join(" "));
      return termos.every((t) => texto.includes(t));  // todos os termos precisam aparecer
    });
    const ordem = $("#ordem").value;
    lista = [...lista].sort((a, b) =>
      ordem === "recentes" ? String(b.atualizado_em).localeCompare(String(a.atualizado_em))
        : ordem === "tamanho" ? b.conhecimentos - a.conhecimentos
          : a.nome.localeCompare(b.nome, "pt-BR"));
    return { lista, termos };
  }

  // ============================================================ 5. CARTÕES
  const CLASSIFICACOES = {
    memoria: "Memória", linguagem: "Linguagem", parametros: "Parâmetros",
    personalizacao: "Personalização", compreensao: "Compreensão", vetores: "Vetores",
    norma: "Norma da língua",
    algoritmo: "Algoritmo", aplicacao: "Aplicação",
  };
  const milhar = (n) => Number(n).toLocaleString("pt-BR");

  /** Selos de origem e classificação. A loja só tem addons oficiais (o catálogo recusa os demais). */
  function selos(a) {
    const origem = `<span class="selo oficial" title="Publicado pela ${esc(a.editor || "Jano Projects")}">${icone("escudo")}Oficial Jano</span>`;
    const tipos = (a.classificacao || []).map((t) =>
      `<span class="selo classe">${esc(CLASSIFICACOES[t] || t)}</span>`).join("");
    return origem + tipos;
  }

  const NOMES_BUSCA = { bm25: "BM25", tfidf: "TF-IDF", fuzzy: "Fuzzy", hibrido: "Híbrido" };
  const NOMES_RESPOSTA = { direta: "Direta", extrativa: "Extrativa" };

  /** Algoritmos recomendados pelo autor (e o acerto no teste com o próprio conteúdo). */
  function recomendacao(a) {
    const r = a.recomendado;
    if (!r) return "";
    const acerto = typeof r.acerto === "number" ? ` · acerto ${Math.round(r.acerto * 100)}% no teste` : "";
    return `<div class="recomendado" title="Configure assim no Aprendiz para o melhor resultado">${icone("check")}
      Recomendado: busca <b>${esc(NOMES_BUSCA[r.busca] || r.busca)}</b> · resposta <b>${esc(NOMES_RESPOSTA[r.resposta] || r.resposta)}</b>${acerto}</div>`;
  }

  /** "Amostra" quando há conhecimentos para mostrar; senão, só "Detalhes" (hash, dependências). */
  const rotuloVer = (a) => ((a.amostra || []).length ? "Amostra" : "Detalhes");

  /** Cor de um addon de tema (só #RRGGBB, já validada pelo catálogo e aqui de novo). */
  function corDoTema(a) {
    const cor = (a.ajustes || []).find((x) => x.chave === "personalizacao.cor");
    return cor && /^#[0-9a-f]{6}$/i.test(cor.valor) ? cor.valor : "";
  }

  /** Prévia de personalização: amostra da cor e o texto de boas-vindas. */
  function ajustes(a) {
    const itens = (a.ajustes || []).map((x) => {
      if (x.chave === "personalizacao.cor" && /^#[0-9a-f]{6}$/i.test(x.valor)) {
        return `<span class="ajuste"><i class="amostra-cor" style="background:${x.valor}"></i>Cor ${esc(x.valor)}</span>`;
      }
      if (x.chave === "personalizacao.boas_vindas") return `<span class="ajuste">Boas-vindas: “${esc(x.valor)}”</span>`;
      if (x.chave === "personalizacao.nome") return `<span class="ajuste">Nome: ${esc(x.valor)}</span>`;
      return `<span class="ajuste">${esc(x.chave)} = ${esc(String(x.valor))}</span>`;
    });
    return itens.length ? `<div class="ajustes">${itens.join("")}</div>` : "";
  }

  function cartao(a, termos) {
    const el = document.createElement("article");
    el.className = "cartao";
    el.innerHTML = `
      <div class="cabecalho">
        <span class="icone-addon"${corDoTema(a) ? ` style="--cor-tema:${corDoTema(a)}"` : ""}>${icone("addon")}</span>
        <div>
          <h3>${destacar(a.nome, termos)}<span class="versao">v${esc(a.versao)}</span></h3>
          <div class="meta">${esc([a.autor && "por " + a.autor, a.categoria].filter(Boolean).join(" · "))}</div>
        </div>
      </div>
      <div class="selos">${selos(a)}</div>
      ${recomendacao(a)}
      <p class="descricao">${destacar(a.descricao, termos)}</p>
      ${ajustes(a)}
      <div class="etiquetas">${(a.etiquetas || []).map((t) =>
        `<button class="etiqueta" data-etiqueta="${esc(t)}">#${destacar(t, termos)}</button>`).join("")}</div>
      <div class="numeros">
        ${a.verbetes ? `<span><b>${a.verbetes}</b> verbetes</span>` : ""}
        ${(a.traducoes || []).length ? `<span><b>${a.traducoes.length}</b> traduções</span>` : ""}
        ${a.conhecimentos - (a.verbetes || 0) ? `<span><b>${a.conhecimentos - (a.verbetes || 0)}</b> conhecimentos</span>` : ""}
        ${a.termos_linguagem ? `<span><b>${a.termos_linguagem}</b> termos de linguagem</span>` : ""}
        ${a.configuracoes ? `<span><b>${a.configuracoes}</b> ${a.configuracoes === 1 ? "configuração" : "configurações"}</span>` : ""}
        ${a.compreensao && a.compreensao.regras ? `<span><b>${milhar(a.compreensao.regras)}</b> regras de compreensão</span>` : ""}
        ${a.compreensao && a.compreensao.lemas ? `<span><b>${milhar(a.compreensao.lemas)}</b> palavras no léxico</span>` : ""}
        ${a.compreensao && a.compreensao.vetores ? `<span>vetores de <b>${milhar(a.compreensao.vetores)}</b> palavras</span>` : ""}
        ${a.norma && a.norma.formas ? `<span>vocabulário de <b>${milhar(a.norma.formas)}</b> formas</span>` : ""}
        ${a.norma && a.norma.regras ? `<span><b>${milhar(a.norma.regras)}</b> regras de gramática</span>` : ""}
        ${a.norma && a.norma.ortografia ? `<span>ortografia: <b>${a.norma.ortografia === "1990" ? "Acordo de 1990" : a.norma.ortografia === "1945" ? "anterior ao Acordo" : "as duas"}</b></span>` : ""}
        ${a.versao_minima_app ? `<span>requer Aprendiz <b>${esc(a.versao_minima_app)}</b>+</span>` : ""}
        <span>${tamanho(a.tamanho)}</span>
        <span>atualizado em ${esc(data(a.atualizado_em))}</span>
      </div>
      <div class="acoes">
        <a class="botao botao-primario" href="${esc(a.arquivo)}" download>${icone("baixar")} Baixar</a>
        <button class="botao ver">${icone("olho")} ${rotuloVer(a)}</button>
      </div>
      <div class="detalhes" hidden>
        <div class="amostra">${(a.amostra || []).map((x) => `
          <div>${x.pergunta ? `<b>${destacar(x.pergunta, termos)}</b>` : ""}<span>${destacar(x.conteudo, termos)}</span></div>`).join("")}
        </div>
        <div class="meta">${esc(a.licenca ? "Licença: " + a.licenca : "")}</div>
        ${(a.dependencias || []).length ? `<div class="meta">Complementa: ${a.dependencias.map((d) =>
          esc(`${d.nome} v${d.versao}`)).join(", ")}</div>` : ""}
        <div class="hash" title="Impressão digital do arquivo: confira se o arquivo baixado é exatamente este">
          ${icone("escudo")} SHA-256 <code>${esc(a.sha256)}</code>
          <button aria-label="Copiar SHA-256">${icone("copiar")}</button>
        </div>
      </div>`;

    el.querySelector(".ver").addEventListener("click", (ev) => {
      const det = el.querySelector(".detalhes");
      det.hidden = !det.hidden;
      ev.currentTarget.innerHTML = `${icone(det.hidden ? "olho" : "x")} ${det.hidden ? rotuloVer(a) : "Fechar"}`;
    });
    el.querySelector(".hash button").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(a.sha256); avisar("SHA-256 copiado."); }
      catch (e) { avisar("Não foi possível copiar."); }
    });
    el.querySelectorAll(".etiqueta").forEach((b) => b.addEventListener("click", () => {
      $("#busca").value = b.dataset.etiqueta;
      renderizar();
      $("#busca").scrollIntoView({ block: "center" });
    }));
    return el;
  }

  function renderizar() {
    const { lista, termos } = filtrar();
    const grade = $("#grade");
    grade.innerHTML = "";
    lista.forEach((a) => grade.appendChild(cartao(a, termos)));
    if (!lista.length) {
      grade.innerHTML = `<div class="vazio">${icone("busca")}<p>Nenhum addon encontrado.
        Tente outra palavra ou escolha "Todas" nas categorias.</p></div>`;
    }
    const total = estado.addons.length;
    $("#resumo").textContent = lista.length === total
      ? `${total} addon${total === 1 ? "" : "s"} disponíve${total === 1 ? "l" : "is"}`
      : `${lista.length} de ${total} addons`;
    $("#limpar-busca").hidden = !$("#busca").value;
    gravarEndereco();
  }

  let espera;
  $("#busca").addEventListener("input", () => { clearTimeout(espera); espera = setTimeout(renderizar, 120); });
  $("#limpar-busca").addEventListener("click", () => { $("#busca").value = ""; renderizar(); $("#busca").focus(); });
  $("#ordem").addEventListener("change", renderizar);

  carregar();
})();
