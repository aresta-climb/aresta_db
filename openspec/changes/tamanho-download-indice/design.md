## Context

O pipeline de geração de artefatos do `aresta_db` é responsável por validar e compilar croquis em YAML para arquivos de protocolo binário (`.binarypb`), otimizar imagens WebP e gerar o `indice.binarypb` que cataloga todos os picos do sistema.

Para permitir que clientes externos (como o `aresta_app`) apresentem antecipadamente o tamanho total de download offline nos cards da interface e banners informativos sem a sobrecarga de disparar dezenas de requisições de rede individuais, o índice consolidará o tamanho agregado em bytes de cada croqui.

Esta proposta formaliza as decisões de design seguindo estritamente os preceitos de `PRINCIPIOS.md`.

## Goals / Non-Goals

**Goals:**
- Estender `PrecomputadosResumoCroqui` no `aresta_api/proto/indice.proto` com o campo escalar `int64 tamanho_download_bytes = 9;`.
- **Library-First (Princípio II)**: Criar a biblioteca modular e autônoma `scripts/calcular_tamanho_croqui_lib.py`, com responsabilidade única de computar a soma em bytes de um croqui (`compilado.binarypb` e imagens válidas em `imagens/`, ignorando pastas de processamento intermediário como `raw_mapas`).
- **Testes de Integração em Primeiro Lugar (Princípio V)**: Estabelecer inicialmente o teste de contrato de integração em `scripts/deploy_generated_test.py` antes da implementação detalhada da biblioteca.
- **TDD e Co-localização (Princípio IV)**: Criar os testes unitários em `scripts/calcular_tamanho_croqui_lib_test.py` no mesmo diretório do arquivo `.py`, cumprindo o ciclo Red-Green-Refactor.
- **100% de Cobertura Unitária (Princípio III)**: Assegurar cobertura total nos novos testes unitários.
- **Simplicidade e Anti-Abstração (Princípio VI)**: Implementar código direto, funcional e declarativo, evitando abstrações ou padrões arquiteturais desnecessários.
- Integrar a biblioteca ao `passo_c_gerar_indice` em `scripts/deploy_generated.py`, gravando o valor em `resumo.precomputados.tamanho_download_bytes` e no `indice.yaml`.

**Non-Goals:**
- Modificar a estrutura ou o conteúdo interno do `compilado.binarypb` dos croquis individuais.
- Criar classes complexas, padrões de projeto pesados (fábricas ou estratégias) para um cálculo aritmético de bytes.
- Alterar o comportamento de undo/redo ou componentes da interface gráfica do editor (Princípio VII inalterado).

## Decisions

### Decisão 1: Extensão Retrocompatível no Protobuf (`aresta_api/proto/indice.proto`)
- **Abordagem**: Declarar `int64 tamanho_download_bytes = 9;` na mensagem `PrecomputadosResumoCroqui`.
- **Justificativa**: A mensagem já hospeda métricas pré-computadas de vias, setores e grupos. Adicionar um campo `int64` preserva total retrocompatibilidade e permite que clientes antigos continuem funcionando sem quebra.
- **Alternativas consideradas**:
  - *Criar uma submensagem de métricas de download*: Descartada por violar o Princípio VI (Simplicidade e Anti-Abstração), já que um único escalar atende perfeitamente ao requisito.

### Decisão 2: Arquitetura Library-First (`scripts/calcular_tamanho_croqui_lib.py`)
- **Abordagem**: Isolar toda a lógica de computação de tamanho em uma biblioteca independente `scripts/calcular_tamanho_croqui_lib.py`, expondo a função:
  `calcular_tamanho_croqui_bytes(caminho_compilado: Path, pasta_imagens: Optional[Path] = None, pastas_excluidas: Optional[Set[str]] = None) -> int`.
- **Justificativa**: Cumpre o Princípio II (Library-First). O script `scripts/deploy_generated.py` já possui quase 1.000 linhas; injetar regras de verificação de arquivos e cálculo diretamente nele aumentaria o acoplamento monolítico. A biblioteca é independente, autossuficiente e fácil de testar.
- **Alternativas consideradas**:
  - *Calcular in-line diretamente dentro do loop de `deploy_generated.py`*: Descartada por violar Library-First e dificultar testes unitários isolados com 100% de cobertura.

### Decisão 3: Estratégia de Testes (Princípios III, IV e V)
- **Abordagem**:
  1. **Fronteira Primeiro (Princípio V)**: Atualizar `scripts/deploy_generated_test.py` com teste simulando a compilação do índice e verificando que `tamanho_download_bytes` é populado no `indice.binarypb` e `indice.yaml` (Red).
  2. **TDD Co-localizado (Princípio IV)**: Criar `scripts/calcular_tamanho_croqui_lib_test.py` no mesmo diretório de `scripts/calcular_tamanho_croqui_lib.py`, cobrindo cenários com imagens normais, pastas inexistentes, arquivos de imagem corrompidos/vazios e exclusão de pastas como `raw_mapas`.
  3. **100% de Cobertura (Princípio III)**: Executar validação de cobertura com `pytest --cov` garantindo que nenhuma linha ou ramo condicional fique desprovido de teste unitário.

### Decisão 4: Simplicidade e Anti-Abstração (Princípio VI)
- **Abordagem**: Utilizar apenas `pathlib.Path` e operações padrão de sistema de arquivos (`stat().st_size`). O código deve ser imperativo/declarativo simples, com tipagem estática e sem classes intermediárias.

## Risks / Trade-offs

- **[Risco] Inclusão indevida de arquivos temporários na contagem de bytes**
  - *Mitigação*: A biblioteca aceita explicitamente um conjunto de subdiretórios a serem ignorados (por padrão recebendo `IMAGENS_SUBDIRS_EXCLUIDOS = {"raw_mapas"}` de `deploy_generated.py`), garantindo que apenas mídias servidas ao usuário final sejam contabilizadas.
- **[Risco] Variação de tamanho caso imagens sejam processadas assincronamente**
  - *Mitigação*: O cálculo é executado no `passo_c_gerar_indice`, momento em que todas as imagens já foram devidamente processadas, otimizadas e copiadas/linkadas no passo A.

## Migration Plan

1. Compilar os protos via `python build.py protos`.
2. Executar o fluxo TDD criando os testes e a biblioteca em `scripts/`.
3. Integrar no script de deploy e validar suite completa (`python build.py test`).
4. Reexecutar o deploy local para inspecionar os valores gerados em `generated/indice.yaml`.

