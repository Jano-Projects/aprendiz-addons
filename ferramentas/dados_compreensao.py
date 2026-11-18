"""
Gera os dados pesados dos addons de compreensão (rodar só quando for
atualizar esses dados; o resultado fica versionado em fontes/):

    fontes/compreensao-portugues/lemas.tsv   ← lemmatization-lists (ODbL-1.0)
    fontes/vetores-portugues/vetores.bin     ← vetores do spaCy pt_core_news_md

Fontes (baixe antes):

  • Lemas: https://github.com/michmech/lemmatization-lists
    arquivo lemmatization-pt.txt — Michal Měchura, Open Database License
    (ODbL-1.0). O lemas.tsv derivado continua sob a ODbL.

  • Vetores: pacote spaCy "pt_core_news_md" (Explosion). Usamos só a tabela
    de vetores (20 mil vetores de 300 dimensões), reduzida a 100 dimensões
    por PCA e guardada em int8.

Uso (num ambiente com spacy, numpy e o modelo instalados):

    python ferramentas/dados_compreensao.py caminho/lemmatization-pt.txt \\
        --app ../aprendiz-dev

O --app aponta para o código do Aprendiz: o script usa a MESMA normalização
e o mesmo radicalizador do app, para que as palavras batam.

Como cada lema é escolhido quando uma forma tem vários ("casas" → casa ou
casar?): vence o lema mais frequente (ordem dos vetores do spaCy, que vem
por frequência). Uma forma que é ela mesma um lema ("canto") fica como está,
exceto formas de verbos irregulares muito comuns ("tinha" → ter, "veio" →
vir). Uma lista de exceções (HOMOGRAFOS) nunca vira lema: substantivos
como "faca", "sede", "dado" e siglas como "ia" (inteligência artificial).
Formas cujo radical já é igual ao do lema não entram como par (o
radicalizador já as junta): entram só como palavra conhecida.
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIMENSOES = 100

IRREGULARES = {"ser", "estar", "ter", "haver", "ir", "vir", "fazer", "dizer", "poder", "querer",
               "saber", "dar", "ver", "por", "trazer", "caber", "ler", "crer", "valer", "ouvir",
               "pedir", "sair", "cair", "perder", "medir", "dormir", "seguir", "sentir",
               "conseguir", "ficar"}
HOMOGRAFOS = set("""faca facas sede sedes dado dados visto vistos posto postos feito feitos dita
ditas ida idas vinda vindas via vias sido era eras fora vera lida lidas lido ouvido ouvidos
pedido pedidos sentido sentidos seguido perdido caida saida saidas valor vale vales cria crias
ditado feita feitas dito vista vistas posta postas dada dadas ponto ia ias""".split())


def sem_acento(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def vetores_spacy():
    import numpy as np
    import spacy
    nlp = spacy.load("pt_core_news_md")
    v = nlp.vocab.vectors
    primeira: dict[int, str] = {}          # linha → palavra original daquela linha
    for chave, linha in v.key2row.items():
        if linha not in primeira:
            try:
                primeira[linha] = nlp.vocab.strings[chave]
            except KeyError:
                pass
    palavras, linhas = [], []
    vistas: set[str] = set()
    for linha in range(v.shape[0]):        # ordem = frequência
        s = primeira.get(linha)
        if not s or not s.islower() or not re.fullmatch(r"[^\W\d_]+", s):
            continue
        p = sem_acento(s)
        if re.fullmatch(r"[a-z]{2,24}", p) and p not in vistas:
            vistas.add(p)
            palavras.append(p)
            linhas.append(linha)
    m = v.data[np.array(linhas)].astype(np.float32)
    m -= m.mean(0)
    _, _, vt = np.linalg.svd(m, full_matrices=False)
    r = m @ vt[:DIMENSOES].T
    r /= np.linalg.norm(r, axis=1, keepdims=True)
    q = np.clip(np.round(r * 127 / np.abs(r).max(1, keepdims=True)), -127, 127).astype(np.int8)
    # Palavras que o spaCy mapeou para um desses vetores ("polegada" → "diâmetro")
    indice_da_linha = {l: i for i, l in enumerate(linhas)}
    apelidos: dict[str, int] = {}
    for chave, linha in v.key2row.items():
        if linha not in indice_da_linha:
            continue
        try:
            s = nlp.vocab.strings[chave]
        except KeyError:
            continue
        if not s.islower() or not re.fullmatch(r"[^\W\d_]+", s):
            continue
        p = sem_acento(s)
        if re.fullmatch(r"[a-z]{3,24}", p) and p not in vistas and p not in apelidos:
            apelidos[p] = indice_da_linha[linha]
    return palavras, q, apelidos


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lemas", type=Path, help="lemmatization-pt.txt")
    parser.add_argument("--app", type=Path, required=True, help="pasta do código do Aprendiz")
    args = parser.parse_args()
    sys.path.insert(0, str(args.app.resolve()))
    from aprendiz.linguagem.normalizador import normalizar
    from aprendiz.linguagem.stemmer import radical
    from aprendiz.recursos import Vetores
    from rapidfuzz.distance import Levenshtein

    palavras, q, apelidos = vetores_spacy()
    frequencia = {p: i for i, p in enumerate(palavras)}

    pares: dict[str, set[str]] = collections.defaultdict(set)
    lemas: set[str] = set()
    for linha in args.lemas.read_text(encoding="utf-8-sig").splitlines():
        lema, _, forma = linha.partition("\t")
        l, f = normalizar(lema), normalizar(forma)
        if not (l.isalpha() and f.isalpha() and len(l) <= 40 and len(f) <= 40):
            continue
        lemas.add(l)
        if f != l:
            pares[f].add(l)

    # Só palavras do léxico entram como apelido de vetor (evita lixo do corpus).
    apelidos = {p: i for p, i in apelidos.items() if p in lemas or p in pares}
    conhecidas = set(palavras) | set(apelidos)

    def ordem(forma: str, lema: str):
        return (frequencia.get(lema, 10**6 + (0 if lema in apelidos else 10**6)),
                Levenshtein.distance(forma, lema), lema)

    tabela: dict[str, str] = {}
    for forma, candidatos in pares.items():
        if forma in HOMOGRAFOS:
            continue
        if forma in lemas:
            irregulares = [l for l in candidatos if l in IRREGULARES]
            if not irregulares:
                continue
            candidatos = set(irregulares)
        lema = min(candidatos, key=lambda l: ordem(forma, l))
        if radical(lema) == radical(forma):
            continue
        if lema in conhecidas or forma in conhecidas:
            tabela[forma] = lema

    # Léxico (palavras conhecidas): as frequentes, os lemas frequentes e todas
    # as formas deles ("comeríamos" entra porque "comer" é frequente).
    comuns = {l for l in lemas if l in conhecidas}
    lexico = sorted(conhecidas | comuns | set(tabela)
                    | {f for f, ls in pares.items() if ls & comuns})
    destino = RAIZ / "fontes" / "compreensao-portugues" / "lemas.tsv"
    with destino.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Derivado de lemmatization-lists (Michal Měchura), ODbL-1.0.\n")
        for p in lexico:
            f.write(f"{p}\t{tabela[p]}\n" if p in tabela else f"{p}\n")
    print(f"{destino}: {len(lexico)} palavras, {len(tabela)} com lema")

    todas = [(p, i) for i, p in enumerate(palavras)] + sorted(apelidos.items())
    vet = Vetores(dimensoes=DIMENSOES, quantidade=len(palavras), palavras=todas,
                  dados=q.tobytes())
    destino = RAIZ / "fontes" / "vetores-portugues" / "vetores.bin"
    destino.write_bytes(vet.como_bytes())
    print(f"{destino}: {len(todas)} palavras, {len(palavras)} vetores "
          f"({destino.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
