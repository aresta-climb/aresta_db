## Why

O código-fonte do motor de processamento e ferramentas do repositório `aresta_db` foi inicialmente disponibilizado sob a licença GNU GPLv3. Embora a GPLv3 garanta copyleft forte, ela impõe restrições severas de vinculação que dificultam a interoperabilidade modular no ecossistema do Aresta.

A migração para a **Mozilla Public License 2.0 (MPL 2.0)** estabelece um copyleft moderno a nível de arquivo (*file-level weak copyleft*), garantindo que qualquer melhoria feita diretamente nos arquivos do `aresta_db` continue aberta para a comunidade, ao mesmo tempo em que permite que outras ferramentas, módulos e integrações consumam e combinem esses componentes com maior flexibilidade e compatibilidade (inclusive com Apache 2.0 e outros projetos).

Realizar essa mudança agora é crucial, pois o repositório ainda não aceitou Pull Requests de colaboradores externos, permitindo que a transição seja feita de forma simples, transparente e juridicamente sólida através de um único commit de relicenciamento, sem a necessidade de CLAs complexos ou autorizações de terceiros.

## What Changes

- **Substituição da Licença Raiz**: O arquivo `LICENSE` na raiz do repositório será atualizado com o texto oficial da Mozilla Public License 2.0 (MPL 2.0).
- **Atualização dos Cabeçalhos SPDX**: Todos os arquivos-fonte (`.py`, scripts de build e ferramentas) com identificador `SPDX-License-Identifier: GPL-3.0-or-later` serão atualizados para `SPDX-License-Identifier: MPL-2.0`.
- **Atualização da Documentação**:
  - `LICENCAS_RESUMO.md`: Ajuste da seção 1 para explicar didaticamente o funcionamento do copyleft a nível de arquivo da MPL 2.0.
  - `README.md`: Atualização das menções à licença de código-fonte de GPLv3 para MPL 2.0.
- **Preservação de Outras Licenças**: A `aresta_api` permanece sob Apache 2.0, a base estruturada de dados (`database/`) permanece sob ODbL 1.0, e textos/mídias continuam sob Copyright dos autores originais.

## Capabilities

### Modified Capabilities
- `open-source-licenses`: Atualização do requisito formal de documentação e vigência da licença do código do motor `aresta_db` de GPLv3 para MPL 2.0.

## Impact

- **Arquivos afetados**: `LICENSE`, `LICENCAS_RESUMO.md`, `README.md`, e todos os arquivos Python e de testes contendo cabeçalho SPDX do repositório.
- **Dependências e APIs**: Nenhuma quebra ou alteração técnica em APIs, modelos ou contratos de compilação.
- **Compatibilidade Jurídica**: Facilita a interoperabilidade de módulos e ferramentas construídas no ecossistema Aresta.
