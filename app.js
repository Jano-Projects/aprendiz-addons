/*
 * Lógica da loja de addons (site 2.0, JavaScript puro).
 *
 *   1. Utilidades (DOM, escape de HTML, formatos, destaque da busca)
 *   2. Tema claro/escuro
 *   3. Grupos e níveis (o que cada grupo significa)
 *   4. Carregar o catálogo e preparar o índice de busca
 *   5. Filtros: grupo, nível, ordem, busca e link compartilhável
 *   6. Lista: grupos, linhas, "mostrar mais" e detalhes sob demanda
 *   7. Pacote: marcar vários addons e baixar um .aprendiz-pacote só (Aprendiz 2.2+)
 *
 * Pensado para catálogos grandes:
 *   • o texto de busca de cada addon é normalizado UMA vez, ao carregar;
 *   • cada grupo mostra LOTE linhas e oferece "mostrar mais";
 *   • os detalhes de um addon só são montados quando a linha é aberta;
 *   • um único ouvinte de clique atende a lista inteira (delegação);
 *   • o CSS usa content-visibility, então linhas fora da tela não são desenhadas.
 *
 * Todo texto vindo do catálogo é escapado antes de ir para a página.
 */
(function () {
  "use strict";

  // ============================================================ 1. UTILIDADES
  const $ = (s, r) => (r || document).querySelector(s);
  const icone = (nome) => `<svg class="ic" aria-hidden="true"><use href="#i-${nome}"/></svg>`;
  const LOTE = 25;

  function esc(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  /** "Atalhos do Windows" → "atalhos do windows" (sem acento, minúsculas), para a busca. */
  function normalizar(texto) {
    return String(texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  /** A amostra vem em Markdown; no site basta o texto: tira **, `, # e marcadores de lista. */
  const semMarkdown = (t) => String(t ?? "").replace(/\*\*|`|^#+\s*/gm, "").replace(/(^|\s)- /g, "$1");

  const milhar = (n) => Number(n).toLocaleString("pt-BR");
  function tamanho(bytes) {
    return bytes < 1024 ? `${bytes} B` : bytes < 1048576
      ? `${(bytes / 1024).toFixed(0)} KB`
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
  function aplicarTema(tema) {
    document.documentElement.dataset.tema = tema;
    $("#btn-tema").innerHTML = icone(tema === "escuro" ? "sol" : "lua");
  }
  let temaSalvo = null;
  try { temaSalvo = localStorage.getItem("loja.tema"); } catch (e) { /* modo privado */ }
  aplicarTema(temaSalvo || (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "escuro" : "claro"));
  $("#btn-tema").addEventListener("click", () => {
    const novo = document.documentElement.dataset.tema === "escuro" ? "claro" : "escuro";
    aplicarTema(novo);
    try { localStorage.setItem("loja.tema", novo); } catch (e) { /* ignora */ }
  });

  // ============================================================ 3. GRUPOS E NÍVEIS
  // A ordem aqui é a ordem na página. "grupo" e "nivel" vêm do catálogo
  // (ferramentas/gerar_catalogo.py, função grupo_e_nivel).
  const GRUPOS = {
    essenciais: {
      nome: "Essenciais",
      texto: "Os alicerces da conversa. Sem eles, o Aprendiz só compara palavras; com eles, " +
        "reconhece o tipo de pergunta, conduz o diálogo e procura pelo sentido. Instale primeiro, nesta ordem.",
    },
    idiomas: {
      nome: "Idiomas e variantes",
      texto: "Como se fala em cada país lusófono: gírias, expressões, grafias e a norma da língua. " +
        "Ative as variantes que você usa; elas respondem a \"o que significa…\" e \"como se diz…\".",
    },
    conhecimento: {
      nome: "Conhecimento",
      texto: "Assuntos prontos para perguntar. Os avançados costumam depender de um básico, " +
        "indicado nos detalhes de cada addon.",
    },
    aparencia: {
      nome: "Aparência",
      texto: "Cores e mensagens de boas-vindas. Mudam só o visual, nunca as respostas.",
    },
  };
  const NIVEIS = { todos: "Todos", basico: "Básico", avancado: "Avançado" };
  const NOME_NIVEL = { base: "essencial", basico: "básico", avancado: "avançado" };
  const NOMES_BUSCA = { bm25: "Rápido · BM25", tfidf: "Didático · TF-IDF", fuzzy: "Tolerante · Fuzzy", hibrido: "Equilibrado · Híbrido" };
  const NOMES_RESPOSTA = { direta: "Fiel · Direta", extrativa: "Resumo · Extrativa" };

  // ============================================================ 4. CATÁLOGO
  const estado = { addons: [], porId: {}, grupo: "todos", nivel: "todos", visiveis: {},
                   selecionados: new Set(), secoes: {} };

  async function carregar() {
    let catalogo;
    try {
      const r = await fetch("catalogo.json", { cache: "no-cache" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      catalogo = await r.json();
    } catch (erro) {
      $("#numeros").textContent = "Não foi possível carregar o catálogo de addons.";
      return;
    }
    estado.addons = (catalogo.addons || []).map((a) => ({
      ...a,
      grupo: GRUPOS[a.grupo] ? a.grupo : "conhecimento",
      // Índice de busca: montado uma vez só.
      _busca: normalizar([a.id, a.nome, a.descricao, a.categoria, ...(a.etiquetas || []),
        ...(a.amostra || []).map((x) => `${x.pergunta || ""} ${x.conteudo}`), ...(a.palavras || []),
        ...(a.traducoes || [])].join(" ")),
    }));
    estado.addons.forEach((a) => { estado.porId[a.id] = a; });
    const essenciais = estado.addons.filter((a) => a.grupo === "essenciais").length;
    $("#numeros").textContent = `${estado.addons.length} addons oficiais · ${essenciais} essenciais` +
      (catalogo.gerado_em ? ` · atualizado em ${new Date(catalogo.gerado_em).toLocaleDateString("pt-BR")}` : "");
    if (catalogo.gerado_em) $("#gerado-em").textContent = "Catálogo gerado em " + new Date(catalogo.gerado_em).toLocaleString("pt-BR");
    lerEndereco();
    renderizar();
  }

  // ============================================================ 5. FILTROS
  /** ?busca=sql&grupo=conhecimento&nivel=avancado&ordem=recentes → busca compartilhável. */
  function lerEndereco() {
    const p = new URLSearchParams(location.search);
    $("#busca").value = p.get("busca") || "";
    estado.grupo = GRUPOS[p.get("grupo")] ? p.get("grupo") : "todos";
    estado.nivel = NIVEIS[p.get("nivel")] ? p.get("nivel") : "todos";
    if (["nome", "recentes", "tamanho"].includes(p.get("ordem"))) $("#ordem").value = p.get("ordem");
  }

  function gravarEndereco() {
    const p = new URLSearchParams();
    const busca = $("#busca").value.trim();
    if (busca) p.set("busca", busca);
    if (estado.grupo !== "todos") p.set("grupo", estado.grupo);
    if (estado.nivel !== "todos") p.set("nivel", estado.nivel);
    if ($("#ordem").value !== "nome") p.set("ordem", $("#ordem").value);
    const q = p.toString();
    history.replaceState(null, "", q ? "?" + q : location.pathname);
  }

  function montarFiltros(contagem) {
    const itens = [["todos", "Todos", estado.addons.length],
      ...Object.entries(GRUPOS).map(([id, g]) => [id, g.nome, contagem[id] || 0])];
    $("#grupos").innerHTML = itens.map(([id, nome, n]) =>
      `<button data-grupo="${id}" class="${id === estado.grupo ? "ativo" : ""}" ${n ? "" : "disabled"}>
        ${esc(nome)}<small>${n}</small></button>`).join("");
    const comNivel = estado.grupo === "todos" || estado.grupo === "conhecimento";
    $("#filtro-nivel").hidden = !comNivel;
    $("#niveis").innerHTML = Object.entries(NIVEIS).map(([id, nome]) =>
      `<button data-nivel="${id}" class="${id === estado.nivel ? "ativo" : ""}">${nome}</button>`).join("");
  }

  function filtrar() {
    const termos = normalizar($("#busca").value).split(/\s+/).filter(Boolean);
    const contagem = {};
    let lista = estado.addons.filter((a) => termos.every((t) => a._busca.includes(t)));
    lista.forEach((a) => { contagem[a.grupo] = (contagem[a.grupo] || 0) + 1; });
    lista = lista.filter((a) =>
      (estado.grupo === "todos" || a.grupo === estado.grupo) &&
      (estado.nivel === "todos" || a.grupo !== "conhecimento" || a.nivel === estado.nivel));
    const ordem = $("#ordem").value;
    lista.sort((a, b) =>
      ordem === "recentes" ? String(b.atualizado_em).localeCompare(String(a.atualizado_em))
        : ordem === "tamanho" ? b.conhecimentos - a.conhecimentos
          : a.nome.localeCompare(b.nome, "pt-BR"));
    return { lista, termos, contagem };
  }

  /** Essenciais na ordem de instalação: quem é dependência vem antes (ordenação topológica). */
  function ordemDeInstalacao(lista) {
    const ids = new Set(lista.map((a) => a.id));
    const feitos = new Set(), saida = [];
    const visitar = (a) => {
      if (feitos.has(a.id)) return;
      feitos.add(a.id);
      (a.dependencias || []).forEach((d) => { if (ids.has(d.id)) visitar(estado.porId[d.id]); });
      saida.push(a);
    };
    lista.forEach(visitar);
    return saida;
  }

  // ============================================================ 6. LISTA
  function etiquetaNivel(a) {
    const cor = (a.ajustes || []).find((x) => x.chave === "personalizacao.cor");
    if (cor && /^#[0-9a-f]{6}$/i.test(cor.valor)) {
      return `<span class="etiq cor"><i style="background:${cor.valor}"></i>${esc(cor.valor)}</span>`;
    }
    if (a.grupo === "idiomas") return `<span class="etiq">${esc(a.regiao || "idioma")}</span>`;
    return `<span class="etiq ${esc(a.nivel)}">${esc(NOME_NIVEL[a.nivel] || a.nivel)}</span>`;
  }

  function linha(a, termos, posicao) {
    return `<article class="addon" data-id="${esc(a.id)}">
      <div class="linha">
        <button class="abrir" aria-expanded="false">
          <span class="titulo">${posicao ? `<span class="mono">${posicao}.</span>` : ""}
            <strong>${destacar(a.nome, termos)}</strong>
            <span class="id">${esc(a.id)} · v${esc(a.versao)}</span></span>
          <p class="desc">${destacar(a.descricao, termos)}</p>
        </button>
        ${etiquetaNivel(a)}
        <span class="lado"><span class="tam">${tamanho(a.tamanho)}</span>
          <label class="marcar" title="Incluir no pacote"><input type="checkbox" data-marcar="${esc(a.id)}"
            ${estado.selecionados.has(a.id) ? "checked" : ""} aria-label="Incluir ${esc(a.nome)} no pacote"></label>
          <a class="baixar" href="${esc(a.arquivo)}" download>${icone("baixar")} Baixar</a></span>
      </div>
    </article>`;
  }

  /** O que o addon traz, em números (só o que existe). */
  function numeros(a) {
    const c = a.compreensao || {}, n = a.norma || {};
    const proprios = a.conhecimentos - (a.verbetes || 0);
    return [
      proprios && ["Conhecimentos", milhar(proprios)],
      a.verbetes && ["Verbetes", milhar(a.verbetes)],
      (a.traducoes || []).length && ["Traduções", milhar(a.traducoes.length)],
      a.termos_linguagem && ["Termos de linguagem", milhar(a.termos_linguagem)],
      c.regras && ["Regras de compreensão", milhar(c.regras)],
      c.lemas && ["Palavras no léxico", milhar(c.lemas)],
      c.vetores && ["Vetores de palavras", milhar(c.vetores)],
      n.formas && ["Formas no vocabulário", milhar(n.formas)],
      n.regras && ["Regras de gramática", milhar(n.regras)],
      a.configuracoes && ["Configurações", a.configuracoes],
    ].filter(Boolean);
  }

  function detalhes(a, termos) {
    const r = a.recomendado;
    const ficha = [
      ...numeros(a),
      r && ["Busca recomendada", NOMES_BUSCA[r.busca] || r.busca],
      r && ["Resposta recomendada", NOMES_RESPOSTA[r.resposta] || r.resposta],
      r && typeof r.acerto === "number" && ["Acerto no teste", Math.round(r.acerto * 100) + "%"],
      a.versao_minima_app && ["Requer Aprendiz", a.versao_minima_app + "+"],
      a.licenca && ["Licença", a.licenca],
      ["Atualizado em", data(a.atualizado_em)],
    ].filter(Boolean);
    const deps = (a.dependencias || []).map((d) => esc(`${d.nome} (v${d.versao}+)`)).join(", ");
    const amostra = (a.amostra || []).map((x) =>
      `<div>${x.pergunta ? `<b>${destacar(x.pergunta, termos)}</b>` : ""}${destacar(semMarkdown(x.conteudo), termos)}</div>`).join("");
    return `<div class="detalhes">
      <div>
        ${amostra ? `<h3>Amostra</h3><div class="amostra">${amostra}</div>` : ""}
        ${deps ? `<h3>Depende de</h3><p>${deps}</p>` : ""}
        ${(a.etiquetas || []).length ? `<h3>Etiquetas</h3><div class="etiquetas">${a.etiquetas.map((t) =>
          `<button data-etiqueta="${esc(t)}">#${destacar(t, termos)}</button>`).join("")}</div>` : ""}
      </div>
      <div>
        <h3>Ficha</h3>
        <dl class="ficha">${ficha.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
        <div class="hash" title="Impressão digital do arquivo: confira se o arquivo baixado é exatamente este">
          ${icone("escudo")} <code>sha256 ${esc(a.sha256)}</code>
          <button data-copiar="${esc(a.sha256)}" aria-label="Copiar SHA-256">${icone("copiar")}</button>
        </div>
      </div>
    </div>`;
  }

  function secao(id, itens, termos) {
    const g = GRUPOS[id];
    const limite = estado.visiveis[id] || LOTE;
    let corpo = "";
    if (id === "essenciais") {
      itens = ordemDeInstalacao(itens);
      corpo += itens.map((a, i) => linha(a, termos, i + 1)).join("");
    } else if (id === "conhecimento" && estado.nivel === "todos") {
      const visiveis = itens.slice(0, limite);
      ["basico", "avancado"].forEach((nivel) => {
        const parte = visiveis.filter((a) => a.nivel === nivel);
        if (parte.length) corpo += `<h3 class="subgrupo">${NIVEIS[nivel]}</h3>` + parte.map((a) => linha(a, termos)).join("");
      });
    } else {
      corpo += itens.slice(0, limite).map((a) => linha(a, termos)).join("");
    }
    if (id !== "essenciais" && itens.length > limite) {
      corpo += `<button class="mais" data-mais="${id}">Mostrar mais ${Math.min(LOTE, itens.length - limite)} de ${itens.length - limite}</button>`;
    }
    estado.secoes[id] = itens.map((a) => a.id);
    return `<section class="grupo" id="g-${id}">
      <header><h2>${esc(g.nome)}</h2><small>${itens.length}</small>
        <button class="marcar-grupo" data-marcar-grupo="${id}">Marcar todos</button></header>
      <p>${esc(g.texto)}</p>${corpo}</section>`;
  }

  let ultimaBusca = { termos: [] };
  function renderizar() {
    const { lista, termos, contagem } = filtrar();
    ultimaBusca = { termos };
    montarFiltros(contagem);
    const html = Object.keys(GRUPOS)
      .map((id) => [id, lista.filter((a) => a.grupo === id)])
      .filter(([, itens]) => itens.length)
      .map(([id, itens]) => secao(id, itens, termos)).join("");
    $("#lista").innerHTML = html || `<p class="vazio">Nenhum addon encontrado. Tente outra palavra ou escolha "Todos" nos grupos.</p>`;
    const total = estado.addons.length;
    $("#resumo").textContent = lista.length === total ? `${total} addons` : `${lista.length} de ${total}`;
    gravarEndereco();
  }

  // Um ouvinte só para a lista inteira (delegação de eventos).
  $("#lista").addEventListener("click", async (ev) => {
    const abrir = ev.target.closest(".abrir");
    if (abrir) {
      const art = abrir.closest(".addon");
      const aberto = art.classList.toggle("aberto");
      abrir.setAttribute("aria-expanded", String(aberto));
      let det = $(".detalhes", art);
      if (aberto && !det) art.insertAdjacentHTML("beforeend", detalhes(estado.porId[art.dataset.id], ultimaBusca.termos));
      else if (det) det.hidden = !aberto;
      return;
    }
    const mais = ev.target.closest("[data-mais]");
    if (mais) {
      estado.visiveis[mais.dataset.mais] = (estado.visiveis[mais.dataset.mais] || LOTE) + LOTE;
      renderizar();
      return;
    }
    const etiqueta = ev.target.closest("[data-etiqueta]");
    if (etiqueta) {
      $("#busca").value = etiqueta.dataset.etiqueta;
      renderizar();
      $("#catalogo").scrollIntoView({ block: "start" });
      return;
    }
    const grupo = ev.target.closest("[data-marcar-grupo]");
    if (grupo) {
      const ids = estado.secoes[grupo.dataset.marcarGrupo] || [];
      const todos = ids.every((id) => estado.selecionados.has(id));
      ids.forEach((id) => (todos ? estado.selecionados.delete(id) : estado.selecionados.add(id)));
      renderizar();
      atualizarBarra();
      return;
    }
    const copiar = ev.target.closest("[data-copiar]");
    if (copiar) {
      try { await navigator.clipboard.writeText(copiar.dataset.copiar); avisar("SHA-256 copiado."); }
      catch (e) { avisar("Não foi possível copiar."); }
    }
  });

  $("#lista").addEventListener("change", (ev) => {
    const caixa = ev.target.closest("[data-marcar]");
    if (!caixa) return;
    if (caixa.checked) estado.selecionados.add(caixa.dataset.marcar);
    else estado.selecionados.delete(caixa.dataset.marcar);
    atualizarBarra();
  });

  // ============================================================ 7. PACOTE
  /** Os marcados + as dependências deles, na ordem de instalação. */
  function doPacote() {
    const ids = new Set();
    const juntar = (id) => {
      const a = estado.porId[id];
      if (!a || ids.has(id)) return;
      ids.add(id);
      (a.dependencias || []).forEach((d) => juntar(d.id));
    };
    estado.selecionados.forEach(juntar);
    return ordemDeInstalacao([...ids].map((id) => estado.porId[id]));
  }

  function atualizarBarra() {
    const barra = $("#barra-pacote");
    const lista = doPacote();
    barra.hidden = !lista.length;
    if (!lista.length) return;
    const extras = lista.length - estado.selecionados.size;
    $("#pacote-resumo").textContent = `${lista.length} ${lista.length === 1 ? "addon" : "addons"}`
      + (extras > 0 ? ` (${extras} por dependência)` : "") + ` · ${tamanho(lista.reduce((t, a) => t + a.tamanho, 0))}`;
  }

  const CRC = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
    return (dados) => { let c = 0xffffffff; for (const b of dados) c = t[(c ^ b) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  })();

  /** ZIP sem compressão (os .aprendiz já são compactados): cabeçalhos locais + diretório central. */
  function zip(arquivos) {
    const enc = new TextEncoder(), partes = [], central = [];
    let posicao = 0;
    for (const { nome, dados } of arquivos) {
      const n = enc.encode(nome), crc = CRC(dados);
      const local = new DataView(new ArrayBuffer(30));
      [[0, 0x04034b50, 4], [4, 20, 2], [14, crc, 4], [18, dados.length, 4], [22, dados.length, 4], [26, n.length, 2]]
        .forEach(([o, v, t]) => (t === 4 ? local.setUint32(o, v, true) : local.setUint16(o, v, true)));
      const cd = new DataView(new ArrayBuffer(46));
      [[0, 0x02014b50, 4], [4, 20, 2], [6, 20, 2], [16, crc, 4], [20, dados.length, 4], [24, dados.length, 4],
        [28, n.length, 2], [42, posicao, 4]].forEach(([o, v, t]) => (t === 4 ? cd.setUint32(o, v, true) : cd.setUint16(o, v, true)));
      partes.push(local, n, dados);
      central.push(cd, n);
      posicao += 30 + n.length + dados.length;
    }
    const tamCentral = central.reduce((t, p) => t + p.byteLength, 0);
    const fim = new DataView(new ArrayBuffer(22));
    [[0, 0x06054b50, 4], [8, arquivos.length, 2], [10, arquivos.length, 2], [12, tamCentral, 4], [16, posicao, 4]]
      .forEach(([o, v, t]) => (t === 4 ? fim.setUint32(o, v, true) : fim.setUint16(o, v, true)));
    return new Blob([...partes, ...central, fim], { type: "application/zip" });
  }

  async function sha256(dados) {
    const h = await crypto.subtle.digest("SHA-256", dados);
    return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  $("#btn-pacote").addEventListener("click", async () => {
    const botao = $("#btn-pacote");
    const lista = doPacote();
    botao.disabled = true;
    try {
      const arquivos = [], indice = [];
      for (const [i, a] of lista.entries()) {
        botao.textContent = `Baixando ${i + 1} de ${lista.length}…`;
        const resposta = await fetch(a.arquivo);
        if (!resposta.ok) throw new Error(`não consegui baixar ${a.nome}`);
        const dados = new Uint8Array(await resposta.arrayBuffer());
        if ((await sha256(dados)) !== a.sha256) throw new Error(`${a.nome} não confere com o SHA-256 do catálogo`);
        const nome = a.arquivo.split("/").pop();
        arquivos.push({ nome, dados });
        indice.push({ arquivo: nome, id: a.id, versao: a.versao, sha256: a.sha256 });
      }
      const pacote = { formato: 1, gerado_em: new Date().toISOString(), addons: indice };
      arquivos.unshift({ nome: "pacote.json", dados: new TextEncoder().encode(JSON.stringify(pacote, null, 2)) });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(zip(arquivos));
      link.download = `aprendiz-${lista.length}-addons.aprendiz-pacote`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 60000);
      avisar("Pacote pronto. No Aprendiz, use Importar addon e escolha o arquivo baixado.");
    } catch (erro) {
      avisar("Não foi possível montar o pacote: " + erro.message);
    } finally {
      botao.disabled = false;
      botao.innerHTML = `${icone("baixar")} Baixar pacote`;
    }
  });
  $("#btn-limpar-pacote").addEventListener("click", () => {
    estado.selecionados.clear();
    renderizar();
    atualizarBarra();
  });

  $("#grupos").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-grupo]");
    if (!b) return;
    estado.grupo = b.dataset.grupo;
    if (estado.grupo !== "todos" && estado.grupo !== "conhecimento") estado.nivel = "todos";
    renderizar();
  });
  $("#niveis").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-nivel]");
    if (!b) return;
    estado.nivel = b.dataset.nivel;
    renderizar();
  });
  let espera;
  $("#busca").addEventListener("input", () => {
    clearTimeout(espera);
    estado.visiveis = {};
    espera = setTimeout(renderizar, 150);
  });
  $("#ordem").addEventListener("change", renderizar);
  // "/" leva à busca, como em buscadores e repositórios de pacotes.
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "/" && !/input|textarea|select/i.test(document.activeElement.tagName)) {
      ev.preventDefault();
      $("#busca").focus();
    }
  });

  carregar();
})();
