<div align="center">

<img src="icone.svg" alt="" width="72">

# Aprendiz · Loja de addons

**Os addons oficiais do [Aprendiz](https://github.com/Jano-Projects/aprendiz-dev)**, o assistente
pessoal local e offline: bases de conhecimento, compreensão do português e aparência, prontas
para baixar e importar.

[![Publicar loja](https://github.com/Jano-Projects/aprendiz-addons/actions/workflows/publicar.yml/badge.svg)](https://github.com/Jano-Projects/aprendiz-addons/actions/workflows/publicar.yml)
[![Homologação](https://github.com/Jano-Projects/aprendiz-addons/actions/workflows/homologacao.yml/badge.svg)](https://github.com/Jano-Projects/aprendiz-addons/actions/workflows/homologacao.yml)
![Plataformas](https://img.shields.io/badge/plataformas-Debian%20%7C%20Fedora%20%7C%20Ubuntu%20%7C%20Windows-6b7280)
![Addons só de dados](https://img.shields.io/badge/addons-s%C3%B3%20dados%2C%20sem%20c%C3%B3digo-16a34a)
[![Licença do site MIT](https://img.shields.io/badge/site-MIT-4f46e5)](LICENSE)

**[Abrir a loja →](https://jano-projects.github.io/aprendiz-addons/)**

</div>

## O que é

O site onde as pessoas encontram e baixam os **addons oficiais** da Jano Projects. Cada addon é
um arquivo `.aprendiz` que se importa no app em **Addons → Importar addon**, com confirmação antes
de instalar. Addons trazem **só dados** (conhecimentos, listas de linguagem, parâmetros, aparência):
nunca código.

Este repositório guarda o site e os addons. O código do Aprendiz fica em
[aprendiz-dev](https://github.com/Jano-Projects/aprendiz-dev).

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

## Plataformas homologadas

A cada envio, os addons são instalados num Aprendiz novo (a `main` do
[aprendiz-dev](https://github.com/Jano-Projects/aprendiz-dev)) e passam pela mesma homologação do
app: 249 perguntas de gente de verdade e a base pessoal de exemplo, com os pisos de acerto
([homologacao.yml](.github/workflows/homologacao.yml)).

| Sistema | Homologação |
|---|---|
| **Debian** (estável) | a cada envio |
| **Fedora** (mais recente) | a cada envio |
| **Ubuntu** (LTS e mais recente) | a cada envio |
| **Windows** | a cada envio |

Além disso, a publicação do site confere cada addon e **não publica** se algum for inválido.

## Documentação

| Para | Leia |
|---|---|
| Publicar ou atualizar um addon | [Publicar um addon](docs/publicar-addon.md) |
| Testar o site, a estrutura do repositório e o desempenho | [Desenvolvimento](docs/desenvolvimento.md) |
| Avisar sobre um addon com problema | [Issues](https://github.com/Jano-Projects/aprendiz-addons/issues/new/choose) · [Segurança](.github/SECURITY.md) |
| Contribuir | [Como contribuir](.github/CONTRIBUTING.md) |

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
