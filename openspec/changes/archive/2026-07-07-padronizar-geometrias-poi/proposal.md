## Why

O processo atual de extração de pontos de interesse (POIs) por OCR gera *bounding boxes* ruidosas e de proporções irregulares, o que polui visualmente os mapas com retângulos de tamanhos aleatórios para itens que deveriam ser uniformes. Além disso, a nomenclatura das geometrias no JSON (usando `circular` e `box`) mistura adjetivos e termos genéricos, o que reduz a semântica. Padronizar as geometrias para formas simétricas com prioridade (círculos e quadrados perfeitos) e unificar a terminologia do banco de dados traz mais consistência aos mapas renderizados, melhora o entendimento do modelo na extração de dados e facilita a manutenção do código. Todo o processo seguirá estritamente os preceitos de qualidade definidos em `PRINCIPIOS.md`, garantindo cobertura total de testes e foco em TDD.

## What Changes

- Padronização semântica das chaves geométricas no JSON de mapas para usar exclusivamente substantivos em português.
- **BREAKING**: Renomeação da propriedade `circular` para `circulo`.
- **BREAKING**: Renomeação da propriedade `box` para `retangulo`.
- Adição formal do suporte à geometria `quadrado` (forçando proporções simétricas para ícones e marcações pequenas que não se encaixam bem em círculos).
- **BREAKING**: Renomeação da propriedade existente `area_livre` para `poligono` (áreas irregulares de múltiplos pontos).
- Modificação das Skills dos Agentes de IA (`mapa_extrair_pontos_de_interesse`) para impor a nova hierarquia de preferência (Círculo > Quadrado > Retângulo) e os novos nomes.
- Criação de uma migração formal (na pasta `migracoes/`) para converter os arquivos `.md` e `.json` existentes. A biblioteca de migração será criada seguindo a regra "Library-First" e TDD.
- Atualização da engine de renderização (Editor e scripts de preview) para interpretar as novas palavras-chave e renderizar adequadamente `quadrado` e `poligono`.
- **Garantia de Qualidade**: 100% de cobertura de testes unitários na lógica de conversão e parsing das formas. Todo código Python resultante será rigorosamente documentado com docstrings em português.

## Capabilities

### New Capabilities
- `poi-geometrias-avancadas`: Adição do formato `quadrado` para forçar consistência visual e renomeação unificada das geometrias para `circulo`, `retangulo` e `poligono`.

### Modified Capabilities
- `editor-mapas`: Atualização do renderizador e lógica de interação do editor para suportar as novas estruturas e nomes (`circulo`, `quadrado`, `retangulo`, `poligono`), respeitando o fluxo TDD na refatoração.

## Impact

- **Banco de Dados (Arquivos YAML/MD em `database/`)**: Todos os arquivos `.md` (e JSONs atrelados se aplicável) que possuam anotações serão alterados pela migração oficial (`box` virará `retangulo`, `area_livre` virará `poligono` e `circular` virará `circulo`). O editor passará a ler e migrar dados antigos automaticamente.
- **Editor UI (`editor/views/widget_editor_mapas.py` e similares)**: Precisa aprender a ler e renderizar/modificar quadrados e polígonos.
- **Scripts Internos (`scripts/`)**: Qualquer script que processe visualmente os mapas precisará de ajustes na leitura do JSON, amparados por testes unitários exaustivos.
- **Qualidade de Software**: A documentação interna via docstrings será enriquecida, cobrindo todos os métodos de leitura e desenho do mapa.
