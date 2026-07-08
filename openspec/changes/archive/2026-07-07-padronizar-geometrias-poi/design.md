## Context

O formato atual dos mapas no sistema armazena Pontos de Interesse (POIs) extraídos por agentes de IA e lidos pelo editor visual. Atualmente, os POIs são marcados com geometrias como `circular`, `box` e `area_livre`. O uso abusivo de `box` gera mapas com marcações visualmente desorganizadas. Além disso, os nomes misturam adjetivos (`circular`) com substantivos/inglês (`box`), o que quebra a semântica do projeto em português estipulada em `PRINCIPIOS.md`.

## Goals / Non-Goals

**Goals:**
- Padronizar a nomenclatura das geometrias do JSON para `circulo`, `quadrado`, `retangulo` e `poligono` (tudo em Português, conforme `PRINCIPIOS.md`).
- Implementar uma biblioteca de migração formal na pasta `migracoes/` para realizar a atualização de dados históricos.
- Atualizar o `widget_editor_mapas.py` (e scripts vizinhos) aplicando a metodologia TDD (Test-Driven Development).
- Garantir **100% de unit test coverage** nas lógicas de processamento de geometria e conversão de arquivos.
- Garantir que cada função e classe modificada tenha documentação detalhada (docstrings).

**Non-Goals:**
- Criar um editor de polígonos ultra complexo no frontend neste momento.

## Decisions

1. **Test-Driven Development (TDD) e Library-First**:
   - Toda a lógica de parseamento das novas geometrias não ficará acoplada nas views do Qt. Ela será encapsulada em módulos de core (ex: `editor/core/geometrias_poi.py`).
   - Os testes serão escritos ANTES da implementação do parser e do script de migração.
2. **Schema Exato para o Quadrado**: Em vez de reutilizar `retangulo`, criaremos um tipo forte `quadrado` com a chave `lado`. Isso blinda a lógica contra quebras ou manipulações errôneas.
3. **Schema Exato para o Polígono**: A chave existente `area_livre` será apenas renomeada para `poligono`, mantendo o seu formato de lista de coordenadas `{"x": int, "y": int}`. Simples, direto e mapeia facilmente para `QPolygonF` no PyQt.
4. **Documentação Rigorosa**: O PR final será inspecionado não apenas para cobertura de código, mas para docstrings descrevendo detalhadamente todos os parâmetros e retornos esperados para lidar com `quadrado` e `poligono`.

## Risks / Trade-offs

- **[Risk] Falha na Migração Automática no Editor**: O editor deve aplicar as migrações automaticamente ao abrir um croqui em versão antiga. O risco é esse pipeline de auto-migração não estar funcionando perfeitamente para as novas geometrias.
  - *Mitigation*: Adicionar testes unitários robustos garantindo que o módulo de leitura do editor consiga disparar e passar a migração `0004_padronizar_geometrias_poi` perfeitamente em `mocks` de arquivos com YAML frontmatter.
- **[Risk] Atraso por Exigência de 100% Coverage**: Testar UI pode ser complicado e baixar a cobertura.
  - *Mitigation*: Separar a lógica de conversão e cálculo das bounding boxes do PyQt, mantendo o negócio 100% coberto. Testes de integração lidarão com as dependências mais pesadas.
