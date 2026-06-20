## Contexto

No modelo atual de `croqui.proto`, as entidades (`ViaEsportiva`, `Boulder`, `Setor`, etc.) contêm informações de apresentação visual nos campos `id_no_mapa`, `id_no_mapa_meio` e `id_no_mapa_fim`. Isso gera um acoplamento reverso onde a entidade precisa conhecer detalhes de sua renderização no mapa, causando problemas quando uma entidade aparece em múltiplos mapas, além de limitar as rotas a uma abstração rígida de 3 pontos. Com o aumento da complexidade dos croquis, surge a necessidade de permitir que o `Mapa` detenha a responsabilidade de "o que" ele está desenhando.

## Objetivos / Não-Objetivos

**Objetivos:**
- Desacoplar a apresentação visual das entidades de dados.
- Permitir uma quantidade ilimitada de pontos (POIs) para descrever a geometria de uma rota.
- Possibilitar "cross-linking" entre mapas, permitindo que mapas referenciem entidades de outros Setores ou Grupos.
- Suportar ajustes finos opcionais de visualização por referência (foco da câmera, nível de zoom).
- Garantir que todas as alterações sejam guiadas por testes (TDD) e alcancem 100% de cobertura de testes unitários (unit test coverage).

**Não-Objetivos:**
- Não iremos refatorar o parseamento de imagens do PDF neste momento, nem modificar o comportamento da UI para desenhar SVG sobre as imagens. (Isso será tratado no repositório de front-end / gateway do app).

## Decisões Arquiteturais e Metodológicas

1. **Referencia no Mapa:** Adição do `repeated Referencia referencias = 6;` no escopo do `Mapa`. Em vez das entidades ditarem em qual POI elas estão, o mapa agrupa POIs (em `ids`) e aponta para a entidade através dos campos textuais `grupo`, `setor`, `escalada`.
2. **Escopo Implícito:** Para facilitar a escrita no YAML e não ser redundante, assumimos que `escalada` sem `setor` referenciado implica que a escalada pertence ao mesmo setor onde o mapa foi declarado. Mapas declarados em nível de Grupo ou Pico que tentarem referenciar uma escalada sem prover o nome do setor deverão gerar um warning no `deploy_generated`.
3. **Migração em Python via TDD:** Um script em Python em `aresta_db/migracoes` fará uso do `ruamel.yaml` para iterar sobre todos os YAMLs locais, encontrar IDs antigos nas entidades e criar os blocos de `referencias` nos mapas pai, mantendo todos os comentários originais do arquivo.
    - **Imperativo TDD:** A lógica de migração e parseamento DEVE ser desenhada via testes (`_test.py`) ANTES da implementação.
    - **100% Coverage:** O código de migração precisará ser testado em 100% das suas linhas para evitar qualquer perda ou corrupção de dados dos croquis.
4. **Política de Migração:** Toda migração deve ser documentada explicitamente em português, então adicionaremos informações sobre isso no repositório. O código será escrito seguindo o princípio de "Library-First", onde a lógica de negócio do parser é independente do script CLI de aplicação em lote.

## Riscos / Trade-offs

- **Risco:** Quebra de compatibilidade em toda a base de dados.
  **Mitigação:** O ciclo Red-Green-Refactor garante que o script funciona isoladamente. O script de migração também deve ser rigorosamente executado no pipeline CI local antes do commit, validando que o `aresta_api` compila sem erros.
- **Risco:** Perda de comentários do YAML.
  **Mitigação:** Utilizaremos a biblioteca `ruamel.yaml` em "RoundTrip mode". Teremos um teste unitário específico que valida se a inserção preserva blocos de comentários pré-existentes.
- **Risco:** Renomeação de escaladas quebrando referências no mapa.
  **Mitigação:** A validação estrita dos dados via Protobuf em build-time já acusa referências perdidas (Dangling pointers).
