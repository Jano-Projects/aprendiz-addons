"""
Gera o catalogo.json da loja a partir dos arquivos em addons/*.aprendiz.

O site (index.html + app.js) só lê esse catálogo. Para publicar um addon:

    1. coloque o arquivo .aprendiz em addons/ (o nome do arquivo = id do addon);
    2. faça o push. O GitHub Actions roda este script e atualiza o site.

Para testar no seu computador:

    python ferramentas/gerar_catalogo.py
    python -m http.server 8000        →  http://localhost:8000

O script recusa addons inválidos (e o site não é atualizado), então um
arquivo quebrado nunca chega a quem baixa. Só usa a biblioteca padrão do Python.

Esta é a loja OFICIAL: só distribui addons da Jano Projects. Cada addon
precisa ser do formato 2 e ter "origem": "oficial" e "editor": "Jano
Projects"; qualquer outro é recusado. Addons de terceiros não passam por
aqui: são compartilhados diretamente, como arquivo, por quem os criou.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_ADDONS = RAIZ / "addons"
DESTINO = RAIZ / "catalogo.json"

PADRAO_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
MAX_JSON = 200 * 1024 * 1024
TAMANHO_AMOSTRA = 6
MAX_ETIQUETAS = 8

# Mesmas regras do app (aprendiz/addons.py): tipo → arquivo; None = traria código.
CLASSIFICACOES = {
    "memoria": "conhecimentos.json",
    "linguagem": "linguagem.json",
    "parametros": "parametros.json",
    "personalizacao": "personalizacao.json",
    "algoritmo": None,
    "aplicacao": None,
}


class Invalido(Exception):
    pass


def ler_json(zip_: zipfile.ZipFile, nome: str, obrigatorio: bool = True):
    try:
        with zip_.open(nome) as f:
            bruto = f.read(MAX_JSON + 1)
    except KeyError:
        if obrigatorio:
            raise Invalido(f"falta o arquivo {nome}") from None
        return None
    if len(bruto) > MAX_JSON:
        raise Invalido(f"{nome} é grande demais")
    try:
        return json.loads(bruto.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise Invalido(f"{nome} não é JSON válido ({erro})") from None


def data_de_atualizacao(arquivo: Path) -> str:
    """Data do último commit que mexeu no arquivo (ou a data do arquivo, fora do Git)."""
    try:
        saida = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(arquivo)],
            cwd=RAIZ, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if saida:
            return saida
    except (OSError, subprocess.SubprocessError):
        pass
    return date.fromtimestamp(arquivo.stat().st_mtime).isoformat()


def amostra(conhecimentos: list[dict]) -> list[dict]:
    """Os primeiros itens, para o visitante ver o tipo de conteúdo antes de baixar."""
    itens = []
    for k in conhecimentos[:TAMANHO_AMOSTRA]:
        conteudo = k.get("conteudo", "")
        itens.append({
            "pergunta": k.get("pergunta") or None,
            "conteudo": conteudo if len(conteudo) <= 220 else conteudo[:217] + "…",
        })
    return itens


def ler_addon(arquivo: Path) -> dict:
    dados = arquivo.read_bytes()
    try:
        zip_ = zipfile.ZipFile(arquivo)
    except zipfile.BadZipFile:
        raise Invalido("não é um arquivo .aprendiz (ZIP) válido") from None
    with zip_:
        m = ler_json(zip_, "manifesto.json")
        if not isinstance(m, dict) or m.get("formato") not in (1, 2):
            raise Invalido("manifesto sem 'formato' 1 ou 2")
        v1 = m["formato"] == 1
        conhecimentos = ler_json(zip_, "conhecimentos.json", obrigatorio=v1) or []
        linguagem = ler_json(zip_, "linguagem.json", obrigatorio=False) or {}
        parametros = {} if v1 else ler_json(zip_, "parametros.json", obrigatorio=False) or {}
        personalizacao = {} if v1 else ler_json(zip_, "personalizacao.json", obrigatorio=False) or {}

    if not isinstance(m.get("id"), str) or not PADRAO_ID.match(m["id"]):
        raise Invalido("id inválido (use letras minúsculas, números e hífen)")
    if arquivo.stem != m["id"]:
        raise Invalido(f"o arquivo deve se chamar {m['id']}.aprendiz")
    for campo in ("nome", "versao"):
        if not isinstance(m.get(campo), str) or not m[campo].strip():
            raise Invalido(f"manifesto sem '{campo}'")
    if not isinstance(conhecimentos, list) or (v1 and not conhecimentos):
        raise Invalido("conhecimentos.json vazio ou inválido")
    if any(not isinstance(k, dict) or not str(k.get("conteudo", "")).strip() for k in conhecimentos):
        raise Invalido("há conhecimento sem 'conteudo'")

    presentes = [t for t, tem in (("memoria", conhecimentos), ("linguagem", linguagem),
                                  ("parametros", parametros), ("personalizacao", personalizacao)) if tem]
    if not presentes:
        raise Invalido("addon vazio")
    if v1:
        raise Invalido("formato 1 não é aceito na loja oficial: gere de novo com o criar_addon.py")
    else:
        classificacao = m.get("classificacao")
        if not isinstance(classificacao, list) or not classificacao:
            raise Invalido("manifesto sem 'classificacao'")
        for tipo in classificacao:
            if tipo not in CLASSIFICACOES:
                raise Invalido(f"classificação desconhecida: {tipo!r}")
            if CLASSIFICACOES[tipo] is None:
                raise Invalido(f"tipo {tipo!r} traria código; a loja só aceita addons de dados")
        if set(classificacao) != set(presentes):
            raise Invalido(f"classificação {classificacao} não bate com o conteúdo {presentes}")
        origem = m.get("origem", "terceiros")
        if origem != "oficial" or m.get("editor") != "Jano Projects":
            raise Invalido("a loja só distribui addons oficiais: o manifesto precisa de "
                           "\"origem\": \"oficial\" e \"editor\": \"Jano Projects\"")
        app = m.get("app") if isinstance(m.get("app"), dict) else {}
        dependencias = [
            {"id": d["id"], "versao": str(d.get("versao") or ""), "nome": str(d.get("nome") or d["id"])}
            for d in (m.get("dependencias") or [])
            if isinstance(d, dict) and isinstance(d.get("id"), str) and PADRAO_ID.match(d["id"])
        ]

    # Algoritmos recomendados (formato 2, opcional): mostrados no site.
    rec = m.get("recomendado") if not v1 else None
    recomendado = None
    if isinstance(rec, dict) and all(isinstance(rec.get(c), str) and re.match(r"^[a-z0-9_-]{1,30}$", rec[c])
                                     for c in ("busca", "resposta")):
        recomendado = {"busca": rec["busca"], "resposta": rec["resposta"]}
        if isinstance(rec.get("acerto"), (int, float)) and 0 <= rec["acerto"] <= 1:
            recomendado["acerto"] = rec["acerto"]

    etiquetas = m.get("etiquetas") or []
    if not isinstance(etiquetas, list):
        etiquetas = []
    termos = 0
    if isinstance(linguagem, dict):
        termos = sum(len(v) for v in linguagem.values() if isinstance(v, (dict, list)))

    return {
        "id": m["id"],
        "nome": m["nome"].strip(),
        "versao": m["versao"].strip(),
        "autor": (m.get("autor") or "").strip() or None,
        "descricao": (m.get("descricao") or "").strip(),
        "licenca": (m.get("licenca") or "").strip() or None,
        "site": m.get("site") or None,
        "categoria": (m.get("categoria") or "Outros").strip(),
        "etiquetas": [str(e).strip() for e in etiquetas if str(e).strip()][:MAX_ETIQUETAS],
        "formato": m["formato"],
        "origem": origem,
        "editor": (m.get("editor") or "").strip() or None,
        "classificacao": classificacao,
        "versao_minima_app": app.get("versao_minima"),
        "criado_com": app.get("criado_com"),
        "dependencias": dependencias,
        "recomendado": recomendado,
        "conhecimentos": len(conhecimentos),
        "verbetes": sum(1 for k in conhecimentos if isinstance(k, dict) and k.get("tipo") == "verbete"),
        # Palavras dos verbetes: deixam a busca do site achar "kota" no dicionário de Angola.
        "palavras": [str(k.get("pergunta")) for k in conhecimentos
                     if isinstance(k, dict) and k.get("tipo") == "verbete" and k.get("pergunta")][:500],
        "termos_linguagem": termos,
        # Valores de parâmetros/personalização, para o site mostrar (ex.: a cor do tema).
        "ajustes": [{"chave": str(k), "valor": v} for k, v in {**parametros, **personalizacao}.items()
                    if isinstance(v, (str, int, float)) and not isinstance(v, bool)][:20],
        "configuracoes": len(parametros) + len(personalizacao),
        "arquivo": f"addons/{arquivo.name}",
        "tamanho": len(dados),
        "sha256": hashlib.sha256(dados).hexdigest(),
        "atualizado_em": data_de_atualizacao(arquivo),
        "amostra": amostra(conhecimentos),
    }


def main() -> None:
    arquivos = sorted(PASTA_ADDONS.glob("*.aprendiz"))
    addons, erros, ids = [], [], set()
    for arquivo in arquivos:
        try:
            addon = ler_addon(arquivo)
            if addon["id"] in ids:
                raise Invalido("id repetido")
            ids.add(addon["id"])
            addons.append(addon)
            print(f"  [ok] {addon['nome']} {addon['versao']} ({addon['conhecimentos']} conhecimentos)")
        except Invalido as erro:
            erros.append(f"{arquivo.name}: {erro}")

    if erros:
        print("\nAddons inválidos (corrija antes de publicar):")
        for e in erros:
            print("  [X]", e)
        sys.exit(1)

    catalogo = {
        "formato": 2,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(addons),
        "addons": sorted(addons, key=lambda a: a["nome"].lower()),
    }
    DESTINO.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n[OK] {DESTINO.name}: {len(addons)} addon(s).")


if __name__ == "__main__":
    main()
