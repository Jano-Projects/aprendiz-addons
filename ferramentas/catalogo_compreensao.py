"""
Gera fontes/compreensao-portugues/compreensao.json a partir de
compreensao-base.json (escrito à mão) + o CATÁLOGO da loja.

O addon de compreensão leva uma cópia resumida da loja: id, nome, descrição e
as PALAVRAS de que cada addon trata. Quando o Aprendiz não sabe responder,
ele compara a pergunta com essas palavras e indica o addon certo — sem
acessar a internet.

Rode sempre que um addon da loja for criado ou mudar, ANTES de gerar o
.aprendiz da compreensão:

    python ferramentas/catalogo_compreensao.py

As palavras saem das perguntas, variações, verbetes e traduções de cada
fonte, das etiquetas e dos termos de região do manifesto. Só usa a
biblioteca padrão do Python.
"""

from __future__ import annotations

import collections
import json
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "fontes"
BASE = FONTES / "compreensao-portugues" / "compreensao-base.json"
DESTINO = FONTES / "compreensao-portugues" / "compreensao.json"
PROPRIOS = {"compreensao-portugues", "vetores-portugues"}
MAX_PALAVRAS = 300

# Palavras que não dizem nada sobre o ASSUNTO de um addon.
GENERICAS = set("""
a ao aos aquilo as assim ate bem com como da das de diga diz do dos e ela elas ele eles em
entao era essa esse esta estar este estou eu fala foi ha isso isto ja lhe mais mas me meu
meus mim minha minhas muito na nas no nos nossa nosso o onde os ou para pela pelas pelo pelos
pode poderia por pouco pra pro quais qual quando quanta quantas quanto quantos que quem sabe
saber sao se sem ser seu seus so sob sobre sua suas tambem te tem tenho ter teu ti tinha tu tua
um uma umas uns voce voces vos significa significado quer dizer fazer faz faco tirar usar
abrir coisa jeito forma algo outro outra mesmo tudo todo toda todos todas cada ainda depois
antes agora aqui ali la sim nao isso dar fica ficar vai vou ir posso quero
""".split())

# Addons só de personalização: o assunto é a aparência, não as palavras do conteúdo.
PALAVRAS_PERSONALIZACAO = ["tema", "visual", "aparencia", "personalizar", "personalizacao"]


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\b([a-z]{1,2})-(?=[a-z])", r"\1", texto)
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def palavras_de_blocos(caminho: Path) -> list[str]:
    """
    Palavras das linhas P:/V: (perguntas e termos). As traduções (T:) ficam de
    fora: são palavras comuns ("dinheiro", "aldeia") e fariam um dicionário
    de gírias ser indicado para qualquer pergunta sobre dinheiro.
    """
    saida = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha[:2].upper() in ("P:", "V:"):
            saida += normalizar(linha[2:]).split()
    return saida


def main() -> None:
    catalogo = []
    for pasta in sorted(p for p in FONTES.iterdir() if p.is_dir()):
        m = json.loads((pasta / "manifesto.json").read_text(encoding="utf-8")) \
            if (pasta / "manifesto.json").exists() else None
        if not m or m["id"] in PROPRIOS:
            continue
        contagem: collections.Counter[str] = collections.Counter()
        for nome in ("perguntas.txt", "verbetes.txt"):
            if (pasta / nome).exists():
                contagem.update(palavras_de_blocos(pasta / nome))
        tem_conteudo = bool(contagem)
        extras = normalizar(" ".join([m["nome"], *(m.get("etiquetas") or []),
                                      *((m.get("regiao") or {}).get("termos") or [])])).split()
        for p in extras:
            contagem[p] += 5  # nome, etiquetas e região pesam mais
        if not tem_conteudo:
            if not (pasta / "personalizacao.json").exists():
                continue
            # Temas: só aparecem para quem quer mudar a aparência. Outros
            # addons de personalização (boas-vindas) ficam com as etiquetas.
            if "tema" in normalizar(" ".join(m.get("etiquetas") or [])).split():
                contagem = collections.Counter({p: 1 for p in PALAVRAS_PERSONALIZACAO})
            else:
                contagem = collections.Counter(normalizar(" ".join(
                    [m["nome"], *(m.get("etiquetas") or [])])).split())
        palavras = [p for p, _ in contagem.most_common()
                    if p not in GENERICAS and len(p) >= 3 and not p.isdigit()][:MAX_PALAVRAS]
        catalogo.append({"id": m["id"], "nome": m["nome"],
                         "descricao": m.get("descricao") or m["nome"], "palavras": palavras})

    dados = json.loads(BASE.read_text(encoding="utf-8"))
    dados["catalogo"] = catalogo
    DESTINO.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{DESTINO.relative_to(RAIZ)}: catálogo com {len(catalogo)} addons")
    for item in catalogo:
        print(f"  {item['id']:34} {len(item['palavras']):3} palavras · {' '.join(item['palavras'][:8])}")


if __name__ == "__main__":
    main()
