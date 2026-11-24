# Como contribuir

A loja publica **só addons oficiais** da Jano Projects, então não recebe addons prontos de
terceiros. As contribuições mais úteis são:

- **Avisar sobre um addon com problema:** resposta errada, informação desatualizada, erro de
  português ou um addon que não instala. Use o formulário
  [Addon com problema](https://github.com/Jano-Projects/aprendiz-addons/issues/new/choose).
- **Sugerir um addon ou um assunto** que falta, pelo formulário *Sugestão de addon*.
- **Melhorar o site** (`index.html`, `estilo.css`, `app.js`) ou as ferramentas, por *pull request*.

## Antes de um pull request

1. Leia [Desenvolvimento](../docs/desenvolvimento.md) e [Publicar um addon](../docs/publicar-addon.md).
2. Rode `python ferramentas/gerar_catalogo.py` e confira que nenhum addon foi recusado.
3. Abra o site localmente (`python -m http.server 8000`) e confira a mudança.
4. **Nada de dados pessoais** nos addons ou nos exemplos: nomes, telefones, senhas e endereços
   precisam ser inventados.

Ao participar, você concorda com o [Código de conduta](CODE_OF_CONDUCT.md).
