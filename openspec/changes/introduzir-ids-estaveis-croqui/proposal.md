# Proposal: Introduzir IDs Estáveis Universais com Pure NanoID 14c

## Why

Atualmente, o ecossistema Aresta Climb referencia escaladas, setores e grupos por meio de cadeias textuais de nomes (strings) e caminhos hierárquicos em toda a base de mapas e navegação. Esse acoplamento textual gera extrema fragilidade: renomear uma via ou alterar sua estrutura exige caçar e reescrever referências em múltiplos arquivos Markdown de mapas, além de introduzir complexidade e lentidão na resolução de rotas no aplicativo móvel.

Além disso, a introdução de placas permanentes de aço inoxidável gravadas a laser nas falésias e a sincronização offline-first com Supabase/PowerSync exigem identificadores estáveis, imutáveis e globais.

Ao invés de adotar uma arquitetura complexa de tabelas intermediárias de mapeamento numérico em YAML (que exigiriam gerenciar dezenas de arquivos extras e ferramentas complexas de resolução de conflitos de merge no Git), adotamos o modelo **Pure NanoID 14c Universal**:
- Um único identificador imutável de 14 caracteres em Base62 (`[0-9a-zA-Z]`, ex: `x8siJek3FiG3aB`).
- Usado universalmente para Croquis, Grupos, Setores, Escaladas e Pontos de Interesse (POIs).
- Elimina completamente qualquer tabela YAML intermediária e qualquer risco de conflito de merge de IDs no Git.
- Alimenta diretamente as placas físicas com o domínio ultra-curto `https://aresta.cc/<uid>` em QR Code de alta resiliência (Nível H, 30% de tolerância a danos).
- Migra croquis experimentais e o acervo existente de forma transparente sem incrementar a versão do serving (`kDataVersion` permanece em `v4`).

## What Changes

- **Pure NanoID 14c Universal**:
  - Toda entidade (`Croqui`, `Grupo`, `Setor`, `Escalada` e `PontoDeInteresse` de mapa) passa a possuir um `uid` permanente de 14 caracteres NanoID Base62 contínuo (`[0-9a-zA-Z]`, ex: `x8siJek3FiG3aB`), com espaço de mais de $1{,}24 \times 10^{25}$ combinações e colisão nula.
  - Eliminação total de tabelas YAML intermediárias de mapeamento (`ids_*.yaml`).
- **Desacoplamento Relacional de Mapas**:
  - As referências de traçados nos mapas deixam de usar nomes textuais e passam a usar exclusivamente `alvo_uid` e `pontos_uids`.
  - Remoção definitiva dos campos textuais `escalada`, `setor` e `grupo` dos arquivos `.md` do `database/`. Renomear uma via torna-se uma edição local de 1 linha no atributo `nome` da via.
- **Renomeação de `label` para `rotulo`**:
  - O campo de exibição visual em `PontoDeInteresse` passa a se chamar `rotulo` (em português brasileiro), sendo atualizado em todo o `database/`, enquanto `label` é marcado como deprecado no Protobuf e mantido com preenchimento duplo no compilado.
- **Placas Físicas e QR Code com `aresta.cc`**:
  - URL canônica curta: `https://aresta.cc/<uid>` (32 caracteres).
  - QR Code Versão 3 (29x29) com Nível H (30% de tolerância a dano físico por arranhão, pó de magnésio ou sol).
- **Suporte a Migrações Database-Only e Script Automático (`0005_migrar_uids_e_rotulos.py`)**:
  - Suporte formal a migrações exclusivas de banco de dados (`AFETA_VERSAO_SERVING = False`), mantendo a versão de serving do app em `v4` sem invalidar os dados locais de produção.
  - Script automático `migracoes/0005_migrar_uids_e_rotulos.py` executado pelo motor de migração (`aplicar_migracoes()`) para migrar croquis experimentais e o acervo histórico via `ruamel.yaml`.
- **Refatoração do Editor Desktop**:
  - Geração nativa de NanoID 14c na criação de nós e POIs.
  - Gravação de `rotulo` em vez de `label`.
  - Simplificação de comandos como `CmdRenomearEscalada` (que não precisa mais tocar em mapas).
- **Testes de Contrato Arquitetural**:
  - Suíte no CI garantindo que nenhum arquivo em `database/` contenha `id:` direto, referências com `escalada`/`setor`/`grupo`, ou campos `label`.
  - Teste de contrato garantindo que a serialização do editor respeita estritamente esse mesmo padrão.
- **Compilador e Retrocompatibilidade (`deploy_generated.py`)**:
  - O compilador injeta os UIDs diretamente no `.binarypb` e preenche em memória os campos legados (`escalada`, `setor`, `grupo` e `label`) para manter funcionamento ininterrupto de versões anteriores do app.

## Capabilities

### New Capabilities
- `identificadores-estaveis`: Governa a geração de NanoIDs 14c universais, a padronização das URLs `aresta.cc/<uid>`, a biblioteca pura `gerenciar_uids_lib`, o suporte a migrações database-only, os testes de contrato e a injeção de compatibilidade no pipeline de deploy.

### Modified Capabilities
- `mapa-referencias-centralizadas`: Atualiza as referências em mapas para utilizarem `alvo_uid` e `pontos_uids` no banco fonte e no compilado, descontinuando a dependência de strings textuais no `database/`, renomeando `label` para `rotulo` e assegurando que o editor opere exclusivamente sob essa convenção.

## Impact

- **Protobufs**: `croqui.proto` e `croqui_experimental.proto` atualizados e recompilados com campos `uid`, `rotulo`, `alvo_uid` e `pontos_uids`.
- **Serving e Migrações**: `serving/update_serving.py` atualizado para respeitar `AFETA_VERSAO_SERVING = False`; criação de `migracoes/0005_migrar_uids_e_rotulos.py`.
- **Banco de Dados (`database/`)**: Todos os arquivos `.md` e `croqui.yaml` ganham `uid` de 14 caracteres, campos `label` viram `rotulo`, e referências de mapas passam a usar `alvo_uid` e `pontos_uids`. Nenhuma tabela intermediária YAML é necessária.
- **Scripts de Deploy**: `deploy_generated.py` e `preparar_submissao_lib.py` atualizados para validar integridade de UIDs e preencher campos legados em memória.
- **Editor Desktop**: Atualização dos fluxos de criação de nós, mapas, serialização e histórico (Undo/Redo).
- **Testes de Contrato**: Nova suíte garantindo conformidade estrutural contínua da pasta `database/` e do editor.
- **Retrocompatibilidade**: O `.binarypb` mantém campos legados populados em memória e serving permanece em `v4`, garantindo funcionamento ininterrupto de versões anteriores do aplicativo.
