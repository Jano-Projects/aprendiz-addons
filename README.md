# Aprendiz · Loja de addons

Loja **oficial** da Jano Projects: o site onde as pessoas encontram e baixam os **addons
oficiais** para o [Aprendiz](https://github.com/Jano-Projects/aprendiz-dev),
o assistente pessoal local e offline.

**Acesse:** https://jano-projects.github.io/aprendiz-addons/

Este repositório guarda apenas o site e os arquivos dos addons. O código do Aprendiz fica em
[aprendiz-dev](https://github.com/Jano-Projects/aprendiz-dev).

## Como funciona

```
addons/*.aprendiz ──► ferramentas/gerar_catalogo.py ──► catalogo.json ──► site (index.html + app.js)
                      (confere cada addon,                (o que o site
                       calcula o SHA-256)                   mostra)
```

A cada push na branch `main`, o GitHub Actions ([publicar.yml](.github/workflows/publicar.yml))
confere os addons, gera o catálogo e publica o site no GitHub Pages. **Se algum addon for
inválido, o site não é atualizado**, então um arquivo quebrado nunca chega a quem baixa.

## Publicar um addon

1. Crie o addon com a ferramenta do Aprendiz (veja o
   [guia de addons](https://github.com/Jano-Projects/aprendiz-dev/blob/main/docs/addons.md)):
   ```bash
   python ferramentas/criar_addon.py fontes/meu-addon -o addons/meu-addon.aprendiz
   ```
2. O arquivo precisa se chamar **`<id>.aprendiz`**, com o mesmo `id` do manifesto.
3. Opcional, só para a loja: no `manifesto.json`, inclua `"categoria"` e `"etiquetas"`. O app
   ignora esses campos.
   ```json
   "categoria": "Tecnologia",
   "etiquetas": ["linux", "terminal"]
   ```
4. Todo addon desta loja leva `"origem": "oficial"` e `"editor": "Jano Projects"` no manifesto.
   O gerador do catálogo recusa qualquer outro.
5. Faça o commit e o push. Em cerca de 1 minuto, o addon aparece no site.

A ferramenta `criar_addon.py` testa os algoritmos com o conteúdo de cada addon e grava no
manifesto a **busca e a resposta recomendadas** (com o acerto no teste). O site mostra essa
recomendação em cada cartão.

Esta loja distribui **somente addons oficiais**. Addons de terceiros (inclusive os exportados
pelo app) não são publicados aqui: quem os cria compartilha o arquivo diretamente. O catálogo
recusa addons do formato 1, de origem diferente de `oficial`, com tipos que trariam código
(`algoritmo`, `aplicacao`) ou cuja classificação não bate com o conteúdo.

**Dicionários** (gírias, regionalismos) usam `verbetes.txt` com blocos `V:`/`R:` e as stopwords
`significa`, `significado`, `quer`, `dizer` no `linguagem.json`; veja `fontes/girias-brasil/`.
**Temas** são só um `personalizacao.json` com `{"personalizacao.cor": "#RRGGBB"}`; veja
`fontes/tema-oceano/`.

Para **atualizar** um addon, aumente a `versao` no manifesto, gere o arquivo de novo e envie.
Quem importar a versão nova no app tem o addon substituído, mantendo a escolha de ativo ou
desativado.

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
├── index.html                       # a página
├── estilo.css                       # visual (claro/escuro, responsivo)
├── app.js                           # busca sem acentos, categorias, ordenação, cartões
├── icone.svg                        # ícone
└── catalogo.json                    # gerado automaticamente; não edite à mão
```

O site não carrega nada de terceiros: sem fontes externas, scripts de análise ou rastreadores.

## Configuração (uma única vez)

No GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## Licenças

- Código do site: [MIT](LICENSE).
- Cada addon tem a própria licença, indicada no manifesto e mostrada no site. Os addons deste
  repositório usam CC0 (domínio público).
