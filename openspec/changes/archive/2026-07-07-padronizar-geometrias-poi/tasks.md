## 1. Setup e TDD - Processamento de Geometrias (Library-First)

- [x] 1.1 Escrever testes unitários em `editor/core/geometrias_poi_test.py` verificando a leitura correta de JSONs com `circulo`, `quadrado`, `retangulo` e `poligono`.
- [x] 1.2 Implementar a lógica de *parsing* e serialização em `editor/core/geometrias_poi.py` para fazer os testes do item 1.1 passarem (TDD).
- [x] 1.3 Adicionar docstrings detalhadas (em português) no módulo `geometrias_poi.py` descrevendo os esquemas e exceções esperadas, conforme `PRINCIPIOS.md`.
- [x] 1.4 Garantir 100% de test coverage para o módulo `geometrias_poi.py`.

## 2. Atualização do Motor de Renderização

- [x] 2.1 Escrever/Atualizar os testes unitários do `widget_editor_mapas_test.py` prevendo a renderização da geometria nova `quadrado` e da rebatizada `poligono`.
- [x] 2.2 Modificar `editor/views/widget_editor_mapas.py` para ler os novos tipos de POIs através da biblioteca desenvolvida no Passo 1.
- [x] 2.3 Implementar a renderização visual simétrica do `quadrado` (usando o `lado`).
- [x] 2.4 Documentar extensivamente com docstrings as funções de desenho de formas.
- [x] 2.5 Refatorar e adicionar testes aos scripts de preview (`scripts/visualizar_mapa_processado.py`) garantindo que 100% do parseamento novo esteja coberto.

## 3. Script de Migração Formal (TDD)

- [x] 3.1 Escrever testes unitários para a migração em `migracoes/0004_padronizar_geometrias_poi_test.py`, criando mocks de textos markdown (`.md`) com YAML frontmatter antigo contendo `"box"`, `"circular"` e `"area_livre"`.
- [x] 3.2 Implementar a migração `migracoes/0004_padronizar_geometrias_poi.py` com a função `migrar(pico_path: Path)` para converter os arquivos e fazer os testes passarem (`circular` -> `circulo`, `box` -> `retangulo`, `area_livre` -> `poligono`).
- [x] 3.3 Adicionar docstrings detalhadas na nova migração.
- [x] 3.4 Incluir testes no fluxo de inicialização do Editor para garantir que ele detecte e rode essa migração (versão 0004) corretamente ao abrir um croqui antigo.
- [x] 3.5 Executar a migração e comitar as alterações resultantes nos `.md` em `database/`.

## 4. Atualização dos Agentes de IA (Skills)

- [x] 4.1 Atualizar `.agents/skills/mapa_extrair_pontos_de_interesse/SKILL.md` (e similares).
- [x] 4.2 Remover a menção aos termos mistos de inglês (`box`) e de adjetivos (`circular`) e substituir por nomes consistentes: `circulo`, `quadrado`, `retangulo` e `poligono`.
- [x] 4.3 Adicionar instrução explícita para preferir o formato: Círculo > Quadrado > Retângulo.
- [x] 4.4 Fornecer um exemplo JSON estrito contendo todos os quatro formatos para consulta imediata do agente.
