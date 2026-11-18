"""
Gera os arquivos de NORMA dos addons de português de cada país (Aprendiz 0.8+):

    fontes/<addon>/norma.json        grafias, equivalências, erros comuns, verbos e regras
    fontes/<addon>/vocabulario.tsv   todas as formas da norma (uma por linha)

Os dois arquivos são GERADOS (não edite à mão) e não ficam no git: são
grandes e saem sempre iguais das fontes. O que se edita fica em
fontes/normas/:

    paises.json          uma entrada por addon: norma, ortografia, vocabulário-base,
                         arquivos de regras e de equivalências que entram
    regras-*.json        regras de gramática (formato em aprendiz/normas.py do app,
                         mais o atalho {"formas_de": ["subir"]}, explicado abaixo)
    equivalencias.tsv    palavras que mudam entre o Brasil e as normas europeia/africanas
    erros-comuns.tsv     escritas erradas comuns e a forma certa (todas as normas)
    grafias-*.tsv        grafias à parte (curadas), com o tipo de cada uma

Fontes dos vocabulários (baixadas na primeira execução, guardadas em .cache-normas/):

  • pt-BR: VERO — Verificador Ortográfico do LibreOffice, de Raimundo Santos
    Moura e colaboradores (LGPL-3.0 / MPL). Já segue o Acordo de 1990.
  • pt-PT: dicionário do Projeto Natura (Universidade do Minho) — José João
    Almeida, Rui Vilela e Alberto Simões (GPL-2.0 / LGPL-2.1 / MPL-1.1). Segue
    o Acordo de 1990 e anota a grafia anterior de cada palavra que mudou
    (PREAO90), que usamos para montar o vocabulário de 1945.

Os dois vêm do repositório de dicionários do LibreOffice. Os vocabulários
derivados mantêm as licenças das fontes (LGPL); o resto do addon é CC BY 4.0.

Atalho nas regras: um elemento {"formas_de": ["subir", "descer"]} vira
{"palavras": [todas as formas desses verbos no vocabulário da norma]}. Assim
"subir para cima" pega "subiu para cima", "subimos pra cima"…

Uso (precisa do pacote spylls, que lê os arquivos do Hunspell):

    pip install spylls
    python ferramentas/dados_normas.py --app ../aprendiz-dev

O --app aponta para o código do Aprendiz, para validar cada norma.json com
a MESMA validação do app antes de gravar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "fontes"
NORMAS = FONTES / "normas"
CACHE = RAIZ / ".cache-normas"

BASE_URL = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master"
DICIONARIOS = {"br": "pt_BR/pt_BR", "pt": "pt_PT/pt_PT"}

CLITICOS = {"me", "te", "se", "lhe", "lhes", "nos", "vos", "o", "a", "os", "as", "lo", "la",
            "los", "las", "no", "na", "nas", "mo", "ma", "mos", "mas", "to", "ta", "tos",
            "tas", "lho", "lha", "lhos", "lhas"}
MESOCLISE = {"ei", "ás", "á", "emos", "eis", "ão", "ia", "ias", "íamos", "íeis", "iam"}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def sem_acento(s: str) -> str:
    d = unicodedata.normalize("NFKD", s)
    return nfc("".join(c for c in d if not unicodedata.combining(c)))


# ---------------------------------------------------------------- download e expansão
def baixar() -> dict[str, str]:
    """Baixa os .dic/.aff (se ainda não estiverem no cache). Devolve os SHA-256."""
    CACHE.mkdir(exist_ok=True)
    hashes = {}
    for nome, caminho in DICIONARIOS.items():
        for ext in ("dic", "aff"):
            destino = CACHE / f"{nome}.{ext}"
            if not destino.exists():
                print(f"  baixando {caminho}.{ext}…")
                with urllib.request.urlopen(f"{BASE_URL}/{caminho}.{ext}") as r:
                    destino.write_bytes(r.read())
            hashes[f"{nome}.{ext}"] = hashlib.sha256(destino.read_bytes()).hexdigest()
    return hashes


def expandir(nome: str) -> list[tuple[str, str]]:
    """Todas as formas (forma, lema) de um dicionário Hunspell. Guardado em cache."""
    cache = CACHE / f"{nome}.formas.tsv"
    if cache.exists():
        return [tuple(l.split("\t")) for l in cache.read_text(encoding="utf-8").splitlines()]
    try:
        from spylls.hunspell import Dictionary
    except ImportError:
        raise SystemExit("Instale o spylls: pip install spylls")
    print(f"  expandindo {nome} (pode levar um minuto)…")
    d = Dictionary.from_files(str(CACHE / nome))
    aff = d.aff

    def sufixos(palavra, flags):
        for f in flags:
            for s in aff.SFX.get(f, []):
                if s.cond_regexp.search(palavra) and (not s.strip or palavra.endswith(s.strip)):
                    base = palavra[: len(palavra) - len(s.strip)] if s.strip else palavra
                    yield base + s.add, s

    def prefixos(palavra, flags):
        for f in flags:
            for p in aff.PFX.get(f, []):
                if p.cond_regexp.search(palavra) and (not p.strip or palavra.startswith(p.strip)):
                    yield p.add + palavra[len(p.strip):], p

    pares: dict[tuple[str, str], None] = {}
    for w in d.dic.words:
        if aff.FORBIDDENWORD and aff.FORBIDDENWORD in w.flags:
            continue
        stem, fl = w.stem, w.flags
        pares[(stem, stem)] = None
        sfx = list(sufixos(stem, fl))
        for forma, s in sfx:
            pares[(forma, stem)] = None
            if s.flags:
                for forma2, _ in sufixos(forma, s.flags):
                    pares[(forma2, stem)] = None
        for forma, p in prefixos(stem, fl):
            pares[(forma, stem)] = None
            if p.crossproduct:
                for forma2, s in sfx:
                    if s.crossproduct:
                        for f3, _ in prefixos(forma2, {p.flag}):
                            pares[(f3, stem)] = None
    saida = [(nfc(f), nfc(l)) for f, l in pares]
    cache.write_text("\n".join(f"{f}\t{l}" for f, l in saida), encoding="utf-8")
    return saida


def anotacoes_natura() -> dict[str, dict[str, str]]:
    """lema → {"CAT": ..., "PREAO90": ...} das anotações do dicionário do Natura."""
    saida = {}
    for linha in (CACHE / "pt.dic").read_text(encoding="utf-8").splitlines()[1:]:
        if "\t" not in linha:
            continue
        palavra, info = linha.split("\t", 1)
        palavra = nfc(palavra.split("/", 1)[0])
        campos = dict(c.split("=", 1) for c in info.strip("[] ").split(",") if "=" in c)
        saida[palavra] = campos
    return saida


def verbo_com_pronome(forma: str) -> bool:
    partes = forma.split("-")
    return len(partes) > 1 and all(p in CLITICOS or p in MESOCLISE for p in partes[1:])


def formas_validas(pares) -> set[str]:
    """Formas para o vocabulário: minúsculas, sem verbo+pronome (o app confere esses)."""
    saida = set()
    for forma, _ in pares:
        f = forma.lower()
        if f and not verbo_com_pronome(f) and re.fullmatch(r"[a-zà-öø-ÿ](?:[a-zà-öø-ÿ'-]{0,58}[a-zà-öø-ÿ.])?", f):
            saida.add(f)
    return saida


# ---------------------------------------------------------------- ortografia anterior
def aplicar_edicao(lema: str, antigo: str, forma: str) -> str | None:
    """
    O Natura diz que "ação" era "acção". Para levar a mudança às flexões
    ("ações" → "acções"), achamos o trecho que mudou entre o lema e a grafia
    antiga (prefixo e sufixo comuns) e o aplicamos na forma, conferindo o
    contexto em volta.
    """
    i = 0
    while i < min(len(lema), len(antigo)) and lema[i] == antigo[i]:
        i += 1
    j = 0
    while (j < min(len(lema), len(antigo)) - i and lema[len(lema) - 1 - j] == antigo[len(antigo) - 1 - j]):
        j += 1
    meio_novo, meio_antigo = lema[i:len(lema) - j], antigo[i:len(antigo) - j]
    depois = lema[len(lema) - j:][:2]
    if forma[:i] != lema[:i] or not forma[i:].startswith(meio_novo):
        return None
    resto = forma[i + len(meio_novo):]
    if depois and not resto.startswith(depois[:1]):
        return None
    return forma[:i] + meio_antigo + resto


def ortografia_anterior_pt(pares_pt, notas) -> dict[str, str]:
    """forma do Acordo → forma anterior, para todas as flexões das palavras anotadas."""
    por_lema = defaultdict(list)
    for forma, lema in pares_pt:
        por_lema[lema].append(forma)
    saida = {}
    for lema, campos in notas.items():
        antigo = campos.get("PREAO90")
        if not antigo:
            continue
        antigo = nfc(antigo.split("$", 1)[0])
        if not re.fullmatch(r"[A-Za-zÀ-ÿ'-]+", antigo):
            continue
        for forma in por_lema.get(lema, [lema]):
            f = forma.lower()
            if verbo_com_pronome(f):
                continue
            velha = aplicar_edicao(lema.lower(), antigo.lower(), f)
            if velha and velha != f:
                saida[f] = velha
    return saida


# Brasil antes de 2009 (Acordo de 1990 obrigatório desde 2016): trema, acentos
# de ditongos abertos em paroxítonas, êem/ôo, acentos diferenciais e hífen.
TREMA = """agüentar argüir argüição bilíngüe cinqüenta cinqüentenário conseqüência conseqüente
delinqüência delinqüente eloqüência eloqüente eqüestre eqüidade eqüino freqüência freqüentar
freqüente lingüiça lingüista lingüística lingüístico pingüim qüinqüenal qüinqüênio sagüi
seqüela seqüência seqüencial seqüestrar seqüestro tranqüilidade tranqüilizar tranqüilo
ungüento aqüífero ambigüidade ambíguo argüido averiguar enxagüar enxágüe apaziguar
redargüir unguento sangüíneo sagüis sequüela""".split()
DITONGOS = """idéia européia européias européu assembléia platéia geléia colméia estréia boléia
epopéia odisséia panacéia onomatopéia alcatéia apnéia diarréia coréia hebréia plebéia atéia
pigméia gonorréia traquéia verborréia seborréia centopéia jibóia bóia jóia paranóia tramóia
claraboia heróico paranóico estóico andróide asteróide celulóide alcalóide esferóide tiróide
debilóide humanóide metalóide ovóide geléias idéias jóias bóias assembléias platéias
estréias epopéias odisséias panacéias jibóias heróicos heróica heróicas estóicos paranóicos
andróides asteróides""".split()
HIATO = """crêem dêem lêem vêem prevêem relêem descrêem revêem antevêem desdêem vôo vôos enjôo
enjôos abençôo perdôo magôo corôo abotôo amontôo povôo assôo dôo môo rôo sôo côo entôo ecôo
atordôo destôo escôo apregôo amaldiçôo""".split()
DIFERENCIAIS = {"pára": "para", "péla": "pela", "pélas": "pelas", "pêlo": "pelo", "pêlos": "pelos",
                "pólo": "polo", "pólos": "polos", "pêra": "pera", "pêras": "peras", "côa": "coa",
                "côas": "coas", "feiúra": "feiura", "baiúca": "baiuca", "bocaiúva": "bocaiuva"}
PREFIXOS_HIFEN = ["anti", "auto", "contra", "extra", "infra", "intra", "semi", "supra", "ultra",
                  "neo", "proto", "pseudo", "arqui", "co", "sobre", "micro", "macro", "mini",
                  "multi", "hiper", "super"]


def ortografia_anterior_br(br: set[str]) -> dict[str, str]:
    """grafia anterior → grafia do Acordo, no Brasil."""
    saida = {}
    for antiga in TREMA + DITONGOS + HIATO:
        antiga = nfc(antiga)
        nova = antiga.replace("ü", "u")
        nova = re.sub("éi", "ei", nova)
        nova = re.sub("ói", "oi", nova)
        nova = nova.replace("êem", "eem").replace("ôo", "oo")
        if nova != antiga and nova in br:
            saida[antiga] = nova
    # Flexões das palavras com trema: todas as formas do vocabulário que
    # começam com o radical sem trema ganham a forma com trema.
    radicais = {nfc(a)[: max(len(a) - 2, 4)] for a in TREMA}
    for forma in br:
        for rad in radicais:
            sem = rad.replace("ü", "u")
            if "ü" in rad and forma.startswith(sem):
                antiga = rad + forma[len(sem):]
                saida.setdefault(antiga, forma)
    for antiga, nova in DIFERENCIAIS.items():
        saida[nfc(antiga)] = nova
    # -óide: todas as palavras terminadas em -oide(s) tinham acento.
    for forma in br:
        if re.search(r"[^aeiou]oides?$", forma):
            saida.setdefault(re.sub(r"oide(s?)$", r"óide\1", forma), forma)
    # Hífen: autoestima ← auto-estima; ultrassom ← ultra-som; contrarregra ← contra-regra.
    for forma in br:
        for p in PREFIXOS_HIFEN:
            if not forma.startswith(p) or len(forma) < len(p) + 4:
                continue
            resto = forma[len(p):]
            if resto[:2] in ("rr", "ss") and resto[1:] in br and p[-1] in "aeiou" and p != "co":
                saida.setdefault(f"{p}-{resto[1:]}", forma)
            elif (resto[0] in "aáeéêiíoóôuú" and sem_acento(resto[0]) != p[-1] and resto in br
                  and p not in ("sobre", "super", "hiper", "micro", "macro", "mini", "multi")):
                saida.setdefault(f"{p}-{resto}", forma)
    return {a: n for a, n in saida.items() if a not in br}


# ---------------------------------------------------------------- grafias entre variantes
TROCAS_ACENTO = [("ô", "ó"), ("ê", "é"), ("ó", "ô"), ("é", "ê"), ("â", "á"), ("á", "â")]


def pares_variantes(origem: set[str], destino: set[str]) -> dict[str, tuple[str, str]]:
    """
    Formas de `origem` que não existem em `destino` e o equivalente lá:
    econômico → económico (acento), recepção → receção (consoante),
    contato → contacto. Devolve forma → (equivalente, tipo).
    """
    so_origem = origem - destino
    saida = {}
    for f in so_origem:
        if "-" in f:
            continue
        candidatos = []
        for de, para in TROCAS_ACENTO:
            pos = f.find(de)
            while pos >= 0:
                candidatos.append((f[:pos] + para + f[pos + 1:], "acento"))
                pos = f.find(de, pos + 1)
        for m in re.finditer(r"[cp](?=[cçt])", f):           # recepção → receção
            candidatos.append((f[:m.start()] + f[m.end():], "consoante"))
        for m in re.finditer(r"(?<=[aeiouáéíóú])(?=[cçt])", f):   # contato → contacto
            for letra in "cp":
                candidatos.append((f[:m.start()] + letra + f[m.start():], "consoante"))
        validos = [(c, t) for c, t in candidatos if c in destino and c not in origem]
        if len(validos) == 1:
            saida[f] = validos[0]
    return saida


# ---------------------------------------------------------------- fontes editáveis
def ler_tsv(caminho: Path) -> list[list[str]]:
    linhas = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        linhas.append([c.strip() for c in linha.split("\t")])
    return linhas


def plural(palavra: str) -> str | None:
    """Plural simples do português (só para gerar a forma plural das equivalências)."""
    if " " in palavra:
        cabeca, resto = palavra.split(" ", 1)
        p = plural(cabeca)
        return f"{p} {resto}" if p else None
    if "-" in palavra:
        cabeca, resto = palavra.split("-", 1)
        p = plural(cabeca)
        return f"{p}-{resto}" if p else None
    for fim, troca in (("ão", "ões"), ("al", "ais"), ("el", "éis"), ("ol", "óis"), ("ul", "uis"),
                       ("il", "is"), ("m", "ns"), ("r", "res"), ("z", "zes"), ("s", None),
                       ("x", None)):
        if palavra.endswith(fim):
            return palavra[: -len(fim)] + troca if troca else None
    return palavra + "s"


def equivalencias(lado: str, norma_id: str = "", converter=None) -> list[dict]:
    """
    equivalencias.tsv: brasil <TAB> europeu <TAB> classe <TAB> nota <TAB> tipo
      brasil/europeu: alternativas separadas por "|" (a primeira é a principal)
      classe: s (substantivo/adjetivo: gera também o plural), x (invariável),
              e (expressão de várias palavras)
      tipo:   vazio (palavras de outra variante) ou "dica-br"/"dica-eu" (falso
              amigo: a palavra existe dos dois lados com sentidos diferentes;
              vira só uma dica, na norma indicada)
      local:  equivalentes próprios de um país, no lugar da coluna europeu:
              "pt-AO=machimbombo|autocarro;pt-MZ=machimbombo|autocarro"
    lado "br" → aponta termos europeus num texto brasileiro; "pt" → o contrário.
    `converter` passa o equivalente para a grafia da norma (1945, em Angola).
    """
    saida = []
    for linha in ler_tsv(NORMAS / "equivalencias.tsv"):
        linha += [""] * (6 - len(linha))
        brasil, europeu, classe, nota, tipo, local = linha[:6]
        lista_br = [nfc(t) for t in brasil.split("|") if t]
        lista_eu = [nfc(t) for t in europeu.split("|") if t]
        pular = False
        for parte in filter(None, local.split(";")):
            pais, _, termos_locais = parte.partition("=")
            if pais.strip() == norma_id and lado != "br":
                if termos_locais.strip() == "-":     # "pt-TL=-": não vale nesta norma
                    pular = True
                lista_eu = [nfc(t) for t in termos_locais.split("|") if t]
        if pular:
            continue
        if converter:
            lista_eu = [" ".join(converter(p) for p in t.split()) for t in lista_eu]
        termos, equivale, uso = ((lista_eu, lista_br, "Portugal e África") if lado == "br"
                                 else (lista_br, lista_eu, "Brasil"))
        meu_lado = "br" if lado == "br" else "eu"
        if tipo.startswith("dica"):
            if tipo != f"dica-{meu_lado}":
                continue
            nivel = "dica"
        else:
            if tipo in ("so-br", "so-eu") and tipo != f"so-{meu_lado}":
                continue
            nivel = "variante"
        item = {"termos": termos[:30], "equivale": " ou ".join(equivale[:2]), "uso": uso,
                "nota": nota, "nivel": nivel}
        saida.append(item)
        if classe == "s":
            plurais = [p for p in (plural(t) for t in termos) if p and p not in termos]
            if plurais:
                saida.append({**item, "termos": plurais[:30],
                              "equivale": " ou ".join(plural(e) or e for e in equivale[:2])})
    return saida


def erros_comuns(vocab: set[str], arquivos: list[str]) -> dict[str, str]:
    saida = {}
    for nome in arquivos:
        for linha in ler_tsv(NORMAS / nome):
            errado, certo = nfc(linha[0].lower()), nfc(linha[1])
            # Só entra se o "errado" não for uma palavra válida nesta norma.
            if " " in errado or errado not in vocab:
                saida[errado] = certo
    return saida


def grafias_curadas(nome: str) -> dict[str, tuple[str, str]]:
    caminho = NORMAS / nome
    if not caminho.exists():
        return {}
    return {nfc(l[0].lower()): (nfc(l[1]), l[2] if len(l) > 2 and l[2] else "variante")
            for l in ler_tsv(caminho)}


def expandir_regras(arquivos: list[str], formas_por_lema: dict[str, set[str]]) -> list[dict]:
    regras = []
    for nome in arquivos:
        for regra in json.loads((NORMAS / nome).read_text(encoding="utf-8")):
            regra = json.loads(json.dumps(regra))
            regra.pop("_comentario", None)
            for el in regra["padrao"]:
                for alvo in (el, el.get("nao") or {}):
                    if "formas_de" in alvo:
                        formas = set()
                        for lema in alvo.pop("formas_de"):
                            formas |= formas_por_lema.get(nfc(lema), set())
                        formas = {f for f in formas if "-" not in f}
                        alvo["palavras"] = sorted(set(alvo.get("palavras", [])) | formas)
            regras.append(regra)
    return regras


# ---------------------------------------------------------------- montagem
def verbos_de(pares, notas=None) -> set[str]:
    """Infinitivos. No Natura, pela categoria; no VERO, por terem gerúndio."""
    if notas is not None:
        return {lema.lower() for lema, c in notas.items() if c.get("CAT") == "v" and c.get("T") == "inf"}
    por_lema = defaultdict(set)
    for forma, lema in pares:
        por_lema[lema].add(forma)
    saida = set()
    for lema, formas in por_lema.items():
        if re.fullmatch(r"[a-zà-öø-ÿ]+[aeioô]r", lema):
            raiz = lema[:-2] if lema != "pôr" else "p"
            vogal = {"a": "a", "e": "e", "i": "i", "o": "o", "ô": "o"}[lema[-2]]
            if f"{raiz}{vogal}ndo" in formas:
                saida.add(lema)
    return saida


def montar(app: Path) -> None:
    sys.path.insert(0, str(app))
    from aprendiz import normas as validacao  # noqa: E402

    hashes = baixar()
    pares_br, pares_pt = expandir("br"), expandir("pt")
    notas = anotacoes_natura()
    br, pt = formas_validas(pares_br), formas_validas(pares_pt)
    print(f"  formas: pt-BR {len(br):,} · pt-PT {len(pt):,}")

    pre_ao_pt = ortografia_anterior_pt(pares_pt, notas)     # forma AO → forma antiga
    antigas = set(pre_ao_pt.values())
    pt_1945 = (pt - set(pre_ao_pt)) | antigas
    print(f"  ortografia anterior (Natura): {len(pre_ao_pt):,} formas mudaram")
    pre_ao_br = ortografia_anterior_br(br)
    print(f"  ortografia anterior (Brasil): {len(pre_ao_br):,} formas")

    br_para_pt = pares_variantes(br, pt)         # forma brasileira → europeia
    pt_para_br = pares_variantes(pt, br)
    print(f"  grafias de variante: BR→PT {len(br_para_pt):,} · PT→BR {len(pt_para_br):,}")

    lemas = {"br": defaultdict(set), "pt": defaultdict(set)}
    for nome, pares in (("br", pares_br), ("pt", pares_pt)):
        for forma, lema in pares:
            lemas[nome][lema.lower()].add(forma.lower())
    verbos = {"br": verbos_de(pares_br), "pt": verbos_de(pares_pt, notas)}

    paises = json.loads((NORMAS / "paises.json").read_text(encoding="utf-8"))
    for addon_id, cfg in paises.items():
        base = cfg["vocabulario"]                 # br | pt | pt-1945 | pt-ambas
        vocab = {"br": br, "pt": pt, "pt-1945": pt_1945, "pt-ambas": pt | antigas}[base]
        lado = "br" if base == "br" else "pt"
        extras = set()
        for arquivo in cfg.get("vocabulario_extra", []):
            extras |= {nfc(l[0].lower()) for l in ler_tsv(NORMAS / arquivo)}
        vocab = vocab | extras

        grafias: dict[str, tuple[str, str]] = {}
        if lado == "br":
            for f, (eq, tipo) in pt_para_br.items():
                grafias[f] = (eq, tipo)
            for antiga, nova in pre_ao_br.items():
                grafias.setdefault(antiga, (nova, "ortografia_anterior"))
        else:
            ortografia = cfg["ortografia"]
            for f, (eq, tipo) in br_para_pt.items():
                if ortografia == "1945":
                    eq = pre_ao_pt.get(eq, eq)
                grafias[f] = (eq, tipo)
            if ortografia == "1990":
                for nova, antiga in pre_ao_pt.items():
                    if antiga not in vocab:
                        grafias.setdefault(antiga, (nova, "ortografia_anterior"))
            elif ortografia == "1945":
                for nova, antiga in pre_ao_pt.items():
                    if nova not in vocab:
                        grafias.setdefault(nova, (antiga, "ortografia_nova"))
        for arquivo in cfg.get("grafias", []):
            grafias.update(grafias_curadas(arquivo))
        grafias = {f: v for f, v in grafias.items() if f != v[0] and f not in extras}

        regras = expandir_regras(cfg["regras"], lemas[lado])
        dados = {
            "norma": {"id": cfg["id"], "nome": cfg["nome"], "pais": cfg["pais"],
                      "ortografia": cfg["ortografia"]},
            "fontes": cfg["fontes"],
            "grafias": {f: v[0] for f, v in sorted(grafias.items())},
            "tipos_grafia": {f: v[1] for f, v in sorted(grafias.items()) if v[1] != "variante"},
            "erros_comuns": {e: " ".join(pre_ao_pt.get(w, w) for w in c.split())
                             if cfg["ortografia"] == "1945" else c
                             for e, c in erros_comuns(vocab, cfg["erros_comuns"]).items()},
            "equivalencias": equivalencias(
                lado, cfg["id"],
                (lambda w: pre_ao_pt.get(w, w)) if cfg["ortografia"] == "1945" else None),
            "verbos": sorted(verbos[lado]),
            "regras": regras,
        }
        validado = validacao.validar_norma(dados)   # a MESMA validação do app
        vocab = {v for v in vocab if validacao._FORMA.match(v)}
        pasta = FONTES / addon_id
        (pasta / "norma.json").write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")),
                                          encoding="utf-8")
        (pasta / "vocabulario.tsv").write_text("\n".join(sorted(vocab)) + "\n", encoding="utf-8")
        print(f"[OK] {addon_id}: {cfg['id']} · {len(vocab):,} formas · "
              f"{len(validado['grafias']):,} grafias · {len(validado['regras'])} regras · "
              f"{len(validado['equivalencias'])} equivalências · "
              f"{len(validado['erros_comuns'])} erros comuns")
    (CACHE / "fontes.sha256.json").write_text(json.dumps(hashes, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera norma.json e vocabulario.tsv dos addons de país.")
    parser.add_argument("--app", type=Path, default=RAIZ.parent / "aprendiz-dev",
                        help="pasta do código do Aprendiz (para validar)")
    args = parser.parse_args()
    montar(args.app.resolve())


if __name__ == "__main__":
    main()
