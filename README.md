# ⛰️ Aresta

Bem-vindo à database aberta do **Aresta**! Nós somos um ecossistema de código aberto dedicado a estruturar, preservar e distribuir informações e a história da escalada em rocha de forma 100% livre.

---

## 🧗 O que é a Escalada e o que é um "Croqui"?

Para quem é leigo no esporte: a escalada em rocha acontece em montanhas, picos e pedreiras ao ar livre. Para que um escalador saiba *por onde* subir na pedra sem se perder ou se colocar em risco, ele usa um mapa chamado **Croqui**. 

Um croqui descreve:
* **As Vias:** O "caminho" imaginário desenhado na pedra.
* **O Grau de Dificuldade:** Quão difícil e físico é subir aquele caminho.
* **A Proteção:** Onde os grampos de segurança de metal estão fincados na rocha.
* **A Chegada (Acesso):** A trilha pela mata necessária para chegar até a base da pedra.

## 🚨 O Problema que o Aresta Resolve

Historicamente, esses croquis foram desenhados à mão, montados em PDFs de editoração eletrônica ou postados em fóruns, e distribuídos de forma fragmentada. 

Hoje, o conhecimento do esporte está se perdendo em links quebrados de blogs dos anos 2000 ou, pior ainda, está sendo "sequestrado" por aplicativos comerciais fechados que pegam o esforço aberto da comunidade e cobram assinaturas para exibi-lo.

O **Aresta** nasceu para resolver isso. Nós extraímos essas informações perdidas e as organizamos em um **Banco de Dados Estruturado** que qualquer pessoa pode baixar, ler e usar para construir aplicativos, mapas e guias impressos, garantindo que o conhecimento coletivo pertença para sempre à própria comunidade. Além disso, fornecemos um app próprio para que a comunidade possa acessar esses dados de forma rápida e intuitiva, com funcionalidades como modo offline, geolocalização, busca inteligente e muito mais.

---

## ✍️ Como editar e melhorar os croquis do Aresta?

Encontrou um grau errado, uma via nova, ou quer ajudar a melhorar as descrições? Sinta-se livre para contribuir! O Aresta é feito pela comunidade e para a comunidade. Temos ferramentas dedicadas para facilitar e agilizar o envio das suas correções.

👉 **[Leia o Guia de Contribuição](./CONTRIBUINDO.md)** para entender rapidamente como submeter correções, dados novos e conhecer nosso processo padrão de validação de autoria.

## 👑 Para Autores de Croquis Originais

Você é o criador, desenhista ou autor de um croqui histórico hospedado no Aresta? Gostaríamos muito de reconhecer o seu esforço e te dar o controle do seu trabalho! 

Convidamos você a reivindicar a autoria da sua obra no sistema. Ao se tornar o **Mantenedor** oficial do seu croqui no repositório, você ganha a palavra final: passará a ter o direito de revisar e aprovar (ou rejeitar) quaisquer sugestões de mudança que a comunidade fizer na sua obra.

👉 **[Leia o Guia para Autores](./AUTORES.md)** para entender como protegemos a sua obra e veja o passo a passo para reivindicar a sua autoria.

## 🛠️ Para Desenvolvedores

Se você é um programador, engenheiro de dados ou quer ajudar a converter PDFs antigos para a nossa base de dados, nós temos ferramentas automatizadas com Inteligência Artificial para facilitar esse trabalho!

👉 **[Leia o Guia do Desenvolvedor](./GUIA_DO_DESENVOLVEDOR.md)** para instruções de como rodar nosso motor, configurar o ambiente Python e usar o nosso Editor Visual de Croquis.

### 🗄️ Catálogo SQLite e Borda (`catalogo.db`)
O ecossistema disponibiliza um catálogo relacional SQLite (`catalogo.db`) normalizado por UID na tabela `catalogo_aresta` (`escalada`, `setor`, `grupo` e `botao`). A resolução textual completa ocorre sem duplicação de strings via `LEFT JOIN`:

```sql
SELECT 
    e.nome AS escalada_nome,
    e.escalada_grau,
    e.escalada_tipo,
    s.nome AS setor_nome,
    g.nome AS grupo_nome,
    c.nome AS pico_nome,
    c.uf AS estado
FROM catalogo_aresta e
LEFT JOIN catalogo_aresta s ON s.uid = e.setor_uid
LEFT JOIN catalogo_aresta g ON g.uid = e.grupo_uid
LEFT JOIN catalogo_croquis c ON c.croqui_uid = e.croqui_uid
WHERE e.uid = ? AND e.tipo = 'escalada';
```

👉 **[Leia a Documentação Completa do Catálogo e Delta Sync](./docs/catalogo_sqlite_e_delta_sync.md)** para detalhes sobre o hash determinístico (`versao_catalogo`), sincronização transacional com o Cloudflare D1 e o gateway `catalogo.arestaclimb.com/sync`.

---

## ⚖️ Licenciamento e Política de Direitos Autorais

O ecossistema Aresta possui um modelo de licenciamento híbrido desenhado para proteger a base contra grandes corporações, mas ser absurdamente amigável para criadores de aplicativos abertos e desenvolvedores independentes:

* O código da nossa API (`aresta_api`) e o motor de processamento de dados (`aresta_db`) são livres sob a **MPL 2.0** (Mozilla Public License 2.0).
* Os metadados estruturados de escalada (os "fatos" do banco de dados) são abertos sob a **ODbL 1.0**.
* Textos longos em Markdown, PDFs históricos e Imagens são hospedados sob o princípio do **Uso Justo (Fair Use)** e pertencem estritamente aos seus autores originais.

Para entender detalhadamente o que você pode ou não fazer com os dados e o código, bem como ler nossa política rigorosa de **Remoção de Conteúdo (Notice and Takedown)** para os autores originais, leia o documento:

👉 **[Resumo de Licenças e Direitos Autorais](./LICENCAS_RESUMO.md)**