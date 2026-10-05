# Proposal: Introduzir IDs Estáveis para Croquis e Entidades

## Why

Atualmente, o ecossistema Aresta Climb referencia escaladas, setores e grupos por meio de cadeias textuais de nomes (strings) e caminhos hierárquicos em toda a base de mapas e navegação. Esse acoplamento textual gera extrema fragilidade: renomear uma via ou alterar sua estrutura exige caçar e reescrever referências em múltiplos arquivos Markdown de mapas, além de introduzir complexidade e lentidão na resolução de rotas no aplicativo móvel.

Além disso, a arquitetura de persistência, sincronização offline-first e comunidade (integrando PowerSync, Supabase e placas físicas de aço inoxidável gravadas a laser nas falésias) exige identificadores numéricos inteiros estáveis e imutáveis de 4 bytes estruturados em **três níveis hierárquicos**:
1. **Nível 1 (Global)**: `croqui_id_numerico` único em todo o catálogo (ex: croqui 12).
2. **Nível 2 (Local - Entidades)**: `entidade_id_numerico` único por croqui para Grupos, Setores e Escaladas (ex: via 35, compondo URLs ultra-curtas nas placas: `app.arestaclimb.com/12/35`).
3. **Nível 3 (Local - Pontos de Interesse)**: `ponto_id_numerico` único por croqui em namespace próprio para nós e POIs de traçados de mapa, impedindo que centenas de pontos vetoriais inflem os IDs de vias ou causem saltos nas placas de inox.

**Importante**: Não há requisito de identificador sequencial estrito (contiguidade obrigatória sem furos) no catálogo global ou localmente nos croquis. Furos/gaps decorrentes de exclusões ou ramificações concorrentes são perfeitamente válidos e esperados. Da mesma forma, não é necessário manter campos de contadores de sequência (como `proximo_croqui_id`) no catálogo em Protobuf: as tabelas YAML são a fonte de verdade para alocação do próximo ID livre.

Para conciliar esses IDs curtos nas placas físicas com a colaboração assíncrona no Git (onde múltiplos colaboradores podem criar vias em paralelo sem risco de colisão de IDs ou conflitos destrutivos de merge), adotamos uma camada de indireção elegante: UIDs permanentes descentralizados no `database/` combinados a tabelas locais de mapeamento (`ids_globais.yaml`, `ids_entidades.yaml` e `ids_pontos.yaml`).

Adicionalmente, garantimos que croquis experimentais e a base existente sejam migrados automaticamente para o novo padrão sem afetar o versionamento de dados de produção do aplicativo móvel (`aresta_app` em `v4`), estabelecendo testes de contrato rigorosos que garantam a ausência definitiva de referências legadas no repositório e nas rotinas do editor.

## What Changes

- **Camada de Indireção com UIDs Descentralizados no `database/`**:
  - Toda entidade (`Croqui`, `Grupo`, `Setor`, `Escalada` e `PontoDeInteresse` de mapa) passa a possuir um `uid` permanente de 12 caracteres NanoID Base62 formatado como `xxxx-xxxx-xxxx` (espaço de mais de $3 \times 10^{21}$ combinações, colisão nula).
  - As referências de traçados nos mapas deixam de usar nomes textuais e passam a usar exclusivamente `alvo_uid` e `pontos_uids`.
  - Remoção definitiva dos campos textuais `escalada`, `setor` e `grupo` dos arquivos `.md` do `database/`.
- **Arquitetura de Três Níveis de Identificadores Numéricos em Tabelas YAML**:
  - **Nível 1 (Global)**: `database/ids_globais.yaml` mapeia `croqui_uid` $\leftrightarrow$ `croqui_id_numerico` (ex: 12).
  - **Nível 2 (Local - Entidades)**: `database/<croqui>/ids_entidades.yaml` mapeia `uid` $\leftrightarrow$ `entidade_id_numerico` (ex: 35) para Grupos, Setores e Escaladas.
  - **Nível 3 (Local - Pontos)**: `database/<croqui>/ids_pontos.yaml` mapeia `uid` $\leftrightarrow$ `ponto_id_numerico` para nós de traçado e POIs de mapa em namespace isolado.
  - **Sem Contiguidade Forçada nem Contadores Globais**: IDs são inteiros únicos estáveis (gaps permitidos); dispensa contadores de sequência no Protobuf do catálogo.
- **Biblioteca Autônoma `scripts/gerenciar_ids_numericos_lib.py`**:
  - Biblioteca autossuficiente e 100% independente do binário Git para geração de UIDs, leitura/escrita de tabelas de IDs nos três níveis, alocação de IDs inteiros livres e resolução semântica de conflitos de merge (usando a técnica de split de visões HEAD vs. Conflitante).
- **Renomeação de `label` para `rotulo`**:
  - O campo de exibição visual em `PontoDeInteresse` passa a se chamar `rotulo` (em português brasileiro), sendo atualizado em todo o `database/`, enquanto `label` é marcado como deprecado no Protobuf e mantido com preenchimento duplo no compilado.
- **Suporte a Migrações Database-Only e Script Automático (`0005_migrar_uids_e_rotulos.py`)**:
  - Introdução formal de suporte a migrações exclusivas de banco de dados (`AFETA_VERSAO_SERVING = False`), permitindo que migrações internas no `database/` e em croquis experimentais sejam executadas sem incrementar a versão do serving (`kDataVersion` permanece 4 no `aresta_app`).
  - Script automático `migracoes/0005_migrar_uids_e_rotulos.py` executado pelo motor de migração (`aplicar_migracoes()`) para migrar croquis experimentais e o acervo histórico de forma transparente e idempotente via `ruamel.yaml`.
- **Refatoração do Editor Desktop**:
  - Atualização do modelo e persistência do editor para gerar e gravar `uid` e `rotulo` para novas entidades e POIs, gerando referências de mapa com `alvo_uid` e `pontos_uids` (sem escrever `id` direto nem strings legadas de caminho).
  - Simplificação de comandos como `CmdRenomearEscalada` (que agora altera apenas o atributo `nome` da via sem tocar em mapas).
- **Testes de Contrato Arquitetural**:
  - Suíte de testes automatizados garantindo que nenhum arquivo em `database/` contenha `id` direto (exceto nos arquivos `ids_*.yaml`), referências com `escalada`/`setor`/`grupo`, ou campos `label`.
  - Teste de contrato garantindo que a serialização do editor respeita estritamente esse mesmo padrão.
- **Compilador e Otimização Extrema de Bytes (`deploy_generated.py`)**:
  - No `compilado.binarypb`, os UIDs são **removidos** para minimizar o tamanho do download offline no app móvel.
  - O compilador injeta os inteiros estáveis `croqui_id_numerico`, `alvo_id` (`entidade_id_numerico`) e `pontos_ids` (`ponto_id_numerico`), além de preencher os campos deprecados `escalada`, `setor`, `grupo` e `label` para assegurar 100% de retrocompatibilidade com clientes antigos.

## Capabilities

### New Capabilities
- `identificadores-estaveis`: Governa a geração de UIDs descentralizados, o gerenciamento das tabelas de mapeamento nos três níveis (`croqui_id_numerico`, `entidade_id_numerico` e `ponto_id_numerico` sem exigência de sequencialidade estrita), a biblioteca pura `gerenciar_ids_numericos_lib`, o suporte a migrações database-only, os testes de contrato e a minificação numérica no pipeline de deploy.

### Modified Capabilities
- `mapa-referencias-centralizadas`: Atualiza as referências em mapas para utilizarem `alvo_uid` e `pontos_uids` no banco fonte, com tradução para `alvo_id` (`entidade_id_numerico`) e `pontos_ids` (`ponto_id_numerico`) no compilado, descontinuando a dependência de strings textuais no `database/`, renomeando `label` para `rotulo` e assegurando que o editor opere exclusivamente sob essa convenção.

## Impact

- **Protobufs**: `croqui.proto`, `indice.proto` e `croqui_experimental.proto` atualizados e recompilados (sem contadores desnecessários no índice).
- **Serving e Migrações**: `serving/update_serving.py` atualizado para respeitar `AFETA_VERSAO_SERVING = False`; criação de `migracoes/0005_migrar_uids_e_rotulos.py`.
- **Banco de Dados (`database/`)**: Todos os arquivos `.md` e `croqui.yaml` ganham `uid`, campos `label` viram `rotulo`, e referências de mapas passam a usar `alvo_uid` e `pontos_uids`. Criação de `ids_globais.yaml`, `ids_entidades.yaml` e `ids_pontos.yaml` mapeando os três níveis.
- **Scripts de Deploy**: `deploy_generated.py` e `preparar_submissao_lib.py` integrados à `gerenciar_ids_numericos_lib.py`.
- **Editor Desktop**: Atualização dos fluxos de criação de nós, mapas, serialização e histórico (Undo/Redo).
- **Testes de Contrato**: Nova suíte garantindo conformidade estrutural contínua da pasta `database/` e do editor.
- **Retrocompatibilidade**: O `.binarypb` mantém campos legados populados em memória e serving permanece em `v4`, garantindo funcionamento ininterrupto de versões anteriores do aplicativo.
