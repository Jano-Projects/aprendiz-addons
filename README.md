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

## Grupos e níveis

O site organiza o catálogo em quatro **grupos**, nesta ordem:

| Grupo | O que reúne | Nível |
|---|---|---|
| **Essenciais** | Compreensão, diálogo e vetores do português: os alicerces da conversa. Sem eles o Aprendiz só compara palavras. O site mostra a **ordem de instalação** (dependências primeiro). | `base` |
| **Idiomas e variantes** | Gírias, expressões, grafias e a norma de cada país lusófono | `basico` |
| **Conhecimento** | Assuntos para perguntar, separados em **Básico** e **Avançado** | `basico` ou `avancado` |
| **Aparência** | Temas de cor e boas-vindas; não mudam as respostas | `basico` |

O grupo e o nível vão para o `catalogo.json` (campos `grupo` e `nivel`). O manifesto pode
declará-los (`"grupo": "conhecimento"`, `"nivel": "avancado"`); sem isso, o gerador deduz
(função `grupo_e_nivel` em `ferramentas/gerar_catalogo.py`):

- classificação `compreensao` ou `vetores` → Essenciais;
- classificação `norma` → Idiomas;
- classificação `personalizacao` → Aparência;
- o resto → Conhecimento, **avançado** se o id tiver `avancado`, `intermediario`, `teoria` ou
  começar com `aprendiz-` (a trilha "Aprendiz por dentro"); senão, básico.

A `categoria` continua no catálogo e na busca, mas não organiza mais a página.

## Publicar um addon

1. Crie o addon com a ferramenta do Aprendiz (veja o
   [guia de addons](https://github.com/Jano-Projects/aprendiz-dev/blob/main/docs/addons.md)):
   ```bash
   python ferramentas/criar_addon.py fontes/meu-addon -o addons/meu-addon.aprendiz \
       --junto addons/compreensao-portugues.aprendiz \
       --junto addons/dialogo-portugues.aprendiz \
       --junto addons/vetores-portugues.aprendiz
   ```
   O `--junto` faz o teste de recomendação com os addons essenciais de linguagem instalados,
   como no uso real.
2. O arquivo precisa se chamar **`<id>.aprendiz`**, com o mesmo `id` do manifesto.
3. Opcional, só para a loja: no `manifesto.json`, inclua `"categoria"`, `"etiquetas"` e, se a
   dedução automática não servir, `"grupo"` e `"nivel"` (veja [Grupos e níveis](#grupos-e-níveis)).
   O app ignora esses campos.
   ```json
   "categoria": "Tecnologia",
   "etiquetas": ["linux", "terminal"],
   "nivel": "avancado"
   ```
   Antes de publicar um addon com `linguagem.json`, confira se ele não briga com os outros
   (com o código do Aprendiz 2.0 ao lado):
   `python ../aprendiz-dev/ferramentas/conferir_addons.py addons/*.aprendiz`.
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

**Dicionários** (gírias, regionalismos) usam `verbetes.txt` com blocos `V:` (o termo; linhas
`V:` a mais são outras grafias), `T:` (as traduções para o português padrão, separadas por
vírgula) e `R:` (o significado), as stopwords `significa`, `significado`, `quer`, `dizer` no
`linguagem.json` e a `regiao` no manifesto (nome, artigo e os termos que as pessoas usam para
falar do lugar). Com isso o app responde nos dois sentidos: "o que significa kota?" e "como se
diz dinheiro em Angola?". Veja `fontes/girias-angola/`.

**Addons de perguntas e respostas** aceitam várias linhas `P:` no mesmo bloco: cada uma é um
jeito diferente de perguntar a mesma coisa. Veja `fontes/atalhos-windows/`.
**Temas** são só um `personalizacao.json` com `{"personalizacao.cor": "#RRGGBB"}`; veja
`fontes/tema-oceano/`.

**Programação** (categoria própria na loja): 20 addons em cinco trilhas encadeadas pelas
`dependencias` do manifesto, do iniciante ao avançado:

| Trilha | Addons |
|---|---|
| Fundamentos | `prog-logica` · `prog-vocabulario` · `prog-estruturas-dados` · `prog-banco-dados` |
| C e C++ | `c-basico` · `c-intermediario` · `c-avancado` · `cpp-basico` · `cpp-intermediario` · `cpp-avancado` |
| SQL | `sql-basico` · `sql-avancado` · `sql-teoria-pratica` (teoria e respostas dos exercícios) |
| Python | `python-basico` · `python-avancado` |
| Aprendiz por dentro | `aprendiz-preparar-ambiente` · `aprendiz-arquitetura` · `aprendiz-codigo` · `aprendiz-algoritmos` · `aprendiz-do-zero` |

As respostas trazem código em blocos de três crases, que o `criar_addon.py` copia como estão
(indentação, linhas em branco, `#include`) a partir da versão posterior à 0.8.0 do Aprendiz.
Antes de publicar, o código foi conferido: os programas C e C++ compilam com `-Wall -Wextra`,
todo o SQL roda no banco de exemplo da loja (o resultado de cada exercício saiu dele), e os
exemplos de Python e do mini-Aprendiz passam nos testes.

Os 20 addons fixam no manifesto a mesma recomendação, **Híbrido · Direta**, para formarem um
grupo só no app ("Usar este grupo"). O `acerto` gravado é o que o `criar_addon.py` mediu para o
Híbrido com o conteúdo de cada addon. O Fuzzy acerta um pouco mais nesse teste, que usa as
próprias perguntas cadastradas; com perguntas escritas de outro jeito e os 20 addons instalados
juntos, o Híbrido acertou mais (71% contra 53% do Fuzzy, em 34 perguntas novas). Para
regenerar a recomendação depois de mudar uma fonte, apague o `recomendado` do manifesto, gere
o addon, anote o acerto do Híbrido e grave-o de volta.

**Compreensão** (Aprendiz 0.7+): os addons `compreensao-portugues` e `vetores-portugues`
ensinam o app a interpretar as perguntas e a indicar o addon certo quando ele não sabe algo.
Eles levam uma cópia resumida desta loja (o catálogo), então, **sempre que um addon for criado
ou mudar**, gere de novo a compreensão:

```bash
python ferramentas/catalogo_compreensao.py      # compreensao-base.json + catálogo → compreensao.json
python ../aprendiz/ferramentas/criar_addon.py fontes/compreensao-portugues -o addons/compreensao-portugues.aprendiz
```

(aumente a `versao` no manifesto). O `lemas.tsv` e o `vetores.bin` só mudam quando as fontes
de dados mudam: veja `ferramentas/dados_compreensao.py`.

A **Compreensão do português 1.4.0** exige o Aprendiz **1.0**: ela traz o tipo de pergunta
`panorama` ("o que você sabe sobre o carro?", "tem algo sobre…", "me lembra o que tenho que
fazer com…"), que junta numa lista tudo o que a base sabe sobre o assunto. Também ganhou
gatilhos de pedido ("me fala", "quero saber", "me lembra", "quero fazer") e mais jeitos de
perguntar o nome do Aprendiz ("você tem nome?", "como te chamam?"). Os gatilhos ficam em
`fontes/compreensao-portugues/compreensao-base.json`; o comportamento está em
"Juntar e reinterpretar", em `docs/compreensao.md` do aprendiz-dev.

**Teia de porquês** (Aprendiz 2.0+): os addons de conhecimento convertidos trazem, em cada bloco
do `perguntas.txt` e antes do `R:`, as linhas `F:` (ref), `A:` (assuntos: os nomes do próprio
conceito, e não temas vizinhos), `Q:` (porquê: `relação | explicação | -> ref`, ou
`-> addon:ref` para outro addon) e `N: raiz`. O `dialogo-portugues` traz a seção `expressao`
(como dizer cada parte da resposta) e o `compreensao-portugues`, a seção `padroes` (estruturas
de frase). Convertidos até agora: `sql-basico`, `sql-avancado`, `sql-teoria-pratica`,
`prog-logica`, `prog-vocabulario`, `prog-estruturas-dados`, `prog-banco-dados`, `python-basico`
e `python-avancado`. Cada leva entra com perguntas próprias na homologação do aprendiz-dev
(`ferramentas/homologar.py`).

**Diálogo** (Aprendiz 0.9+): `dialogo-portugues` traz só a seção `dialogo` de um
`compreensao.json` (cumprimentos, palavras de conversa, continuações e atos de fala: pedir
ajuda, desabafar, pedir opinião, "não entendi", "sim"...). É escrito à mão em
`fontes/dialogo-portugues/compreensao.json`; não entra no catálogo da compreensão.

**Grupos no app**: addons de apoio (compreensão, diálogo, vetores, boas-vindas) não têm
recomendação própria e entram no grupo dos addons que declaram em `"dependencias"` ou em
`"complementa"` no manifesto. A compreensão e o diálogo declaram os oito addons de português:

```json
"complementa": ["girias-brasil", "girias-portugal", "girias-angola", "girias-mocambique",
                "expressoes-cabo-verde", "expressoes-guine-bissau",
                "expressoes-sao-tome-e-principe", "expressoes-timor-leste"]
```

**Normas da língua** (Aprendiz 0.8+): os oito addons de português de cada país (Brasil,
Portugal, Angola, Moçambique, Cabo Verde, Guiné-Bissau, São Tomé e Príncipe e Timor-Leste)
trazem, além dos verbetes, um `norma.json` (grafias, erros comuns, equivalências entre
variantes, verbos e regras de gramática) e um `vocabulario.tsv` com todas as formas da
norma. Esses dois arquivos são **gerados** e não ficam no git; o que se edita está em
`fontes/normas/`. Para gerar de novo (precisa do pacote `spylls` e de internet para baixar os
dicionários do LibreOffice na primeira vez):

```bash
pip install spylls
python ferramentas/dados_normas.py --app ../aprendiz
python ../aprendiz/ferramentas/criar_addon.py fontes/girias-brasil -o addons/girias-brasil.aprendiz
```

Os verbetes podem ter uma **variedade** (linha `L:`, declarada em `regiao.variedades` no
manifesto): uma região do país ou uma língua que convive com o português. Veja
`fontes/girias-brasil/`.

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

## Configuração (uma única vez)

No GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## Licenças

- Código do site: [MIT](LICENSE).
- Cada addon tem a própria licença, indicada no manifesto e mostrada no site (CC BY 4.0 ou
  CC0, na maioria).
- **Compreensão do português**: ODbL 1.0. Os lemas derivam de
  [lemmatization-lists](https://github.com/michmech/lemmatization-lists), de Michal Měchura
  (ODbL 1.0).
- **Vetores de palavras do português**: CC BY-SA 4.0. Os vetores derivam do pacote
  `pt_core_news_md` do [spaCy](https://spacy.io/models/pt), da Explosion.
- **Addons de português de cada país** (3.0): os verbetes, as regras e as respostas são
  CC BY 4.0. Os vocabulários derivam de dicionários livres do LibreOffice e mantêm a licença
  deles: o do Brasil, do [VERO](https://pt-br.libreoffice.org/projetos/projeto-vero-verificador-ortografico/)
  (Raimundo Santos Moura e colaboradores, LGPL-3.0 / MPL); os de Portugal, dos países
  africanos e de Timor-Leste, do [Projeto Natura](https://natura.di.uminho.pt/) da
  Universidade do Minho (José João Almeida, Rui Vilela e Alberto Simões; GPL-2.0 /
  LGPL-2.1 / MPL-1.1).
