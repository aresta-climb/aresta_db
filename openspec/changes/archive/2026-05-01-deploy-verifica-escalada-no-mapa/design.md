## Context

O script `scripts/deploy_generated.py` é responsável por consolidar os dados dos croquis e gerar o índice para o frontend. Atualmente, ele delega a compilação para `scripts/preparar_submissao_lib.py`, que por sua vez utiliza o Protobuf para serialização. No entanto, não há verificações de integridade referencial entre os campos de texto que representam IDs no mapa e os pontos de interesse reais definidos nos objetos de mapa.

## Goals / Non-Goals

**Goals:**
- Criar uma rotina de validação robusta e reutilizável para integridade de IDs de mapa.
- Garantir que erros de digitação nos arquivos YAML sejam capturados antes do deploy.
- Prover mensagens de erro claras que ajudem o autor a localizar o problema (arquivo e nome da via).
- Manter a performance do deploy alta através de buscas eficientes (uso de `set`).

**Non-Goals:**
- Não serão validadas coordenadas geográficas ou bounding boxes nesta etapa.
- Não haverá correção automática de IDs (apenas relato de erro).
- Não serão validados outros tipos de referências cruzadas além dos IDs de mapa.

## Decisions

### 1. Localização da Lógica de Validação
**Decisão**: Implementar a lógica em uma nova função `validar_referencias_mapa` dentro de `scripts/preparar_submissao_lib.py`.
**Racional**: Segue o princípio "Library-First", permitindo que tanto o script de deploy quanto o editor (no futuro) possam realizar a mesma validação.

### 2. Estrutura da Validação
**Decisão**: Para cada Setor ou Grupo, pré-processar todos os seus mapas e coletar todos os `id` de `pontos_de_interesse` em um `set`.
**Racional**: Permite verificação O(1) para cada ID referenciado nas escaladas, garantindo que o tempo de validação seja negligenciável.

### 3. Tratamento de Erros no Deploy
**Decisão**: Modificar o loop em `passo_a_compilar_croquis` para capturar exceções de validação específicas, acumular as mensagens de erro por croqui e continuar o processamento dos demais croquis.
**Racional**: Atende ao requisito de não interromper o deploy global por causa de um único erro, mas ainda falhar o processo ao final se houver erros.

## Risks / Trade-offs

- **[Risco]** Croquis muito grandes com centenas de mapas e vias podem ter um pequeno impacto no tempo de deploy.
  - **Mitigação**: O uso de `set` para busca de IDs torna o processo extremamente rápido mesmo em escalas maiores.
- **[Risco]** Mudanças no esquema do Protobuf podem quebrar a validação.
  - **Mitigação**: A validação será escrita de forma genérica, iterando sobre os tipos de escalada conhecidos.
