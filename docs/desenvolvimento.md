# Desenvolvimento da loja

## Como funciona

```
addons/*.aprendiz ──► ferramentas/gerar_catalogo.py ──► catalogo.json ──► site (index.html + app.js)
                      (confere cada addon,                (o que o site
                       calcula o SHA-256)                   mostra)
```

A cada push na branch `main`, o GitHub Actions ([publicar.yml](../.github/workflows/publicar.yml))
confere os addons, gera o catálogo e publica o site no GitHub Pages. **Se algum addon for
inválido, o site não é atualizado**, então um arquivo quebrado nunca chega a quem baixa.

## Testar no seu computador

```bash
python ferramentas/gerar_catalogo.py
python -m http.server 8000
```

Depois, abra http://localhost:8000.

## Estrutura

```
aprendiz-addons/
├── .github/workflows/publicar.yml   # confere os addons e publica no GitHub Pages
├── addons/                          # os arquivos .aprendiz que o site oferece para baixar
├── fontes/                          # o texto-fonte de cada addon (perguntas.txt, manifesto…)
├── ferramentas/gerar_catalogo.py    # gera o catalogo.json (só biblioteca padrão do Python)
├── ferramentas/catalogo_compreensao.py  # catálogo da loja dentro do addon de compreensão
├── ferramentas/dados_compreensao.py     # gera lemas.tsv e vetores.bin (precisa de spaCy)
├── ferramentas/dados_normas.py          # gera norma.json e vocabulario.tsv dos países (precisa de spylls)
├── fontes/normas/                       # fontes das normas: regras, equivalências, erros comuns…
├── index.html                       # a página (topo, catálogo, instalar, criar)
├── estilo.css                       # visual de catálogo com as cores do app; claro/escuro
├── app.js                           # grupos, níveis, busca sem acentos, lista leve e detalhes sob demanda
├── icone.svg                        # ícone
└── catalogo.json                    # gerado automaticamente; não edite à mão
```

O site não carrega nada de terceiros: sem fontes externas, scripts de análise ou rastreadores.

### Desempenho com muitos addons

O site foi pensado para catálogos grandes (testado com 3.000 addons: cerca de 1 s para
carregar e desenhar):

- o texto de busca de cada addon é preparado uma vez só, ao carregar;
- cada grupo mostra 25 linhas e oferece **Mostrar mais**;
- os detalhes (amostra, ficha, SHA-256) só são montados quando a linha é aberta;
- um único ouvinte de clique atende a lista inteira;
- o CSS usa `content-visibility`, então o navegador não desenha linhas fora da tela.

Endereços compartilháveis: `?busca=sql&grupo=conhecimento&nivel=avancado&ordem=recentes`.
A tecla <kbd>/</kbd> leva à busca.

## Configuração do GitHub Pages (uma única vez)

No GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
