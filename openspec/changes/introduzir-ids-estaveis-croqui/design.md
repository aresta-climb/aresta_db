# Technical Design: Introduzir IDs Estáveis para Croquis e Entidades

## Context

O Aresta Climb utiliza Protobuf Edition 2023 (`croqui.proto` e `indice.proto`) para serialização de croquis e catálogos. O armazenamento-fonte no Git (`database/`) utiliza arquivos YAML (`croqui.yaml`) e Markdown com YAML Frontmatter (`grupo_*.md`, `setor_*.md`).

Historicamente, as conexões entre mapas visuais e dados eram mantidas através de triplas textuais `(grupo, setor, escalada)` em `Mapa.Referencia`. Com a introdução da arquitetura de sincronização offline-first (PowerSync + Supabase) e links físicos permanentes (placas de aço inox na rocha), há a necessidade imperativa de identificadores numéricos inteiros estáveis (`int32`) estruturados em **três níveis hierárquicos**:
1. **Nível 1 (Global)**: `croqui_id_numerico` único no catálogo.
2. **Nível 2 (Local - Entidades)**: `entidade_id_numerico` único no escopo de cada croqui para Grupos, Setores e Escaladas (viabilizando URLs ultra-curtas nas placas: `app.arestaclimb.com/12/35`).
3. **Nível 3 (Local - Pontos de Interesse)**: `ponto_id_numerico` único no escopo de cada croqui para pontos de interesse e nós de traçados de mapa em namespace isolado.

Para garantir que colaboradores trabalhando em forks e branches concorrentes no Git não sofram colisões de IDs nem conflitos de merge em arquivos de conteúdo, adotamos uma **Camada de Indireção com Mapeamento de Densidade**:
- UIDs descentralizados de 12 caracteres (Base62) nos arquivos de conteúdo.
- Tabelas de mapeamento biunívocas em YAML nos três níveis (`ids_globais.yaml`, `ids_entidades.yaml` e `ids_pontos.yaml`).
- Minificação numérica e remoção de UIDs no `.binarypb` compilado.
- Suporte a migrações com escopo "database-only", isolando o versionamento interno do repositório da versão de serving consumida pelo aplicativo móvel (`kDataVersion = 4`).

Ver `proposal.md` para motivação e `specs/` para os requisitos contratuais.

## Goals / Non-Goals

**Goals:**
- Atribuir UIDs descentralizados permanentes (`xxxx-xxxx-xxxx`, NanoID Base62 12c) para todas as entidades e POIs de mapa no `database/`.
- Estruturar a identificação numérica em três níveis hierárquicos: `croqui_id_numerico` (global), `entidade_id_numerico` (entidades locais) e `ponto_id_numerico` (pontos locais de mapa).
- Desacoplar referências em mapas, adotando `alvo_uid` e `pontos_uids` no banco fonte, eliminando a dependência de strings textuais no `database/`.
- Adotar tabelas de mapeamento biunívocas e enxutas nos três níveis (`ids_globais.yaml`, `ids_entidades.yaml`, `ids_pontos.yaml`) contendo estritamente `id` e `uid`.
- Não impor contiguidade numérica estrita (gaps/furos são válidos) e não depender de campos contadores no Protobuf do catálogo.
- Implementar a biblioteca autônoma `scripts/gerenciar_ids_numericos_lib.py`, 100% independente do binário do Git, com resolução semântica de conflitos de merge baseada em split de visões.
- Substituir o termo `label` por `rotulo` (em português brasileiro) no Protobuf e nos arquivos fontes.
- Criar suporte a migrações "database-only" (`AFETA_VERSAO_SERVING = False`) para permitir evoluir dados internos e croquis experimentais sem alterar o serving de produção (`kDataVersion` permanece 4).
- Implementar o script de migração automática `migracoes/0005_migrar_uids_e_rotulos.py` para croquis experimentais e acervo.
- Refatorar o editor desktop para produzir e manipular nativamente UIDs, `rotulo` e referências relacionais sem campos depreciados.
- Implementar testes de contrato rigorosos garantindo que nem a pasta `database/` nem o editor contenham ou emitam campos legados (`id` direto em entidades, `escalada`/`setor`/`grupo` em referências, ou `label`).
- Remover os UIDs do `compilado.binarypb` final para garantir disciplina estrita de bytes e downloads compactos no aplicativo móvel.
- Traduzir os UIDs para inteiros estáveis nos três níveis (`croqui_id_numerico`, `alvo_id` via `entidade_id_numerico`, `pontos_ids` via `ponto_id_numerico`) no compilado e preencher strings legadas para retrocompatibilidade total.

**Non-Goals:**
- Não exigir sequencialidade contígua estrita (furos decorrentes de deleções ou merges são permitidos; não reindexar entidades existentes).
- Não criar campos contadores de sequência em schemas Protobuf (como `proximo_croqui_id` no `Indice` ou `proximo_id` no `Croqui`).
- Não forçar dependência do binário Git em tempo de execução para compilação ou deploy.
- Não incrementar o serving do app para `v5` (a compatibilidade do binário compilado com `v4` é mantida integralmente).
- Não manter os UIDs dentro do `.binarypb` final entregue aos usuários do app.

## Decisions

### 1. UIDs Descentralizados e NanoID Base62 com 12 Caracteres (`xxxx-xxxx-xxxx`)

- Toda entidade (`Croqui`, `Grupo`, `Setor`, `Escalada` e `PontoDeInteresse`) recebe um identificador único descentralizado em formato Base62 (`[0-9a-zA-Z]`) com 12 caracteres formatado como `xxxx-xxxx-xxxx` (ex: `k7X9-m2P1-qRt4`).
- **Espaço amostral**: $62^{12} \approx 3{,}22 \times 10^{21}$ combinações.
- **Probabilidade de colisão**: para $N = 100.000$ entidades, a probabilidade é inferior a $1{,}5 \times 10^{-12}$ (zero prático).
- **Case Sensitivity**: Válido e seguro em todos os sistemas operacionais, pois o UID é apenas o valor de um campo de texto dentro de arquivos `.md` e `.yaml` (nunca nome de pasta ou arquivo no filesystem).

### 2. Arquitetura em Três Níveis, Ausência de Sequencialidade Estrita e Separação de Namespaces

A arquitetura organiza os identificadores numéricos de 4 bytes em **três níveis independentes**:

1. **Nível 1 (Global - `croqui_id_numerico`)**:
   - Mapeado em `database/ids_globais.yaml`.
   - Atribui um identificador estável único global a cada croqui do catálogo (`croqui_uid` $\leftrightarrow$ `croqui_id_numerico`, ex: 12).
   - Utilizado no índice (`indice.proto`), roteamento do app e prefixo das placas físicas.

2. **Nível 2 (Local - `entidade_id_numerico`)**:
   - Mapeado em `database/<croqui>/ids_entidades.yaml`.
   - Atribui identificador estável para as entidades principais de escalada (`Grupo`, `Setor`, `Escalada`).
   - Garante números compactos para placas físicas gravadas a laser na rocha (ex: via 35 $\rightarrow$ `app.arestaclimb.com/12/35`).
   - Referenciado em mapas pelo campo compilado `alvo_id`.

3. **Nível 3 (Local - `ponto_id_numerico`)**:
   - Mapeado em `database/<croqui>/ids_pontos.yaml`.
   - Namespace próprio e isolado para `PontoDeInteresse` e nós de traçados vetoriais de mapas.
   - **Vantagem crítica**: impede que centenas de nós de linhas ou POIs visuais intermediários inflem a contagem das vias ou causem saltos indesejados nas placas de inox.
   - Referenciado em mapas pelo campo compilado `pontos_ids`.

**Gaps Permitidos e Eliminação de Contadores Centrais:**
- Não há requisito de contiguidade estrita (1, 2, 3... sem furos). Se uma via ou setor for removido, seu ID simplesmente deixa de ser referenciado, sem forçar renumerações ou compactações em cascata.
- Não há campos como `proximo_croqui_id` no Protobuf do catálogo nem contadores em arquivos `.yaml`. A alocação de novos IDs consulta diretamente o arquivo de mapeamento YAML correspondente para obter o próximo inteiro livre (ex: `max(ids) + 1` ou qualquer ID vago).

```text
  database/
  ├── ids_globais.yaml                <-- Nível 1: croqui_uid <-> croqui_id_numerico (ex: 12)
  └── br_mg_sabara_pedra_rachada/
      ├── ids_entidades.yaml          <-- Nível 2: uid <-> entidade_id_numerico (Grupos, Setores, Escaladas)
      ├── ids_pontos.yaml             <-- Nível 3: uid <-> ponto_id_numerico (Pontos de Interesse de Mapas)
      ├── croqui.yaml
      └── grupo_*.md / setor_*.md
```

Estrutura dos arquivos (estritamente `id` e `uid`, sem nomes ou slugs redundantes):
```yaml
ids_entidades:
- id: 1
  uid: "k7X9-m2P1-qRt4"
- id: 2
  uid: "a1B2-c3D4-e5F6"
```

### 3. Remoção de Strings Textuais das Referências de Mapas no `database/`

- No `database/`, as referências passam a ser puramente relacionais via UIDs:
  ```yaml
  referencias:
  - alvo_uid: "k7X9-m2P1-qRt4"
    pontos_uids:
    - "m7K2-v9T1-wR48"
    - "p9A2-b8C1-xY34"
  ```
- **Eliminação de acoplamento**: Os campos `escalada`, `setor` e `grupo` são deletados dos arquivos Markdown de mapas. Renomear uma via torna-se uma edição pontual de 1 linha no atributo `nome` daquela via. O comando `CmdRenomearEscalada` no editor fica livre de varrer ou alterar mapas.
- No Protobuf, `escalada`, `setor` e `grupo` são marcados como `[deprecated = true]`.

### 4. Adoção do Termo `rotulo` em `PontoDeInteresse`

- Substituição de `label` por `rotulo` no Protobuf:
  ```protobuf
  string rotulo = 12 [(aresta.texto_na_ui) = "Rótulo na Imagem"];
  string label = 2 [deprecated = true];
  ```
- No `database/`, todos os campos `label:` são migrados para `rotulo:`.
- O compilador preenche tanto `rotulo` quanto `label` no `.binarypb` para garantir retrocompatibilidade com versões antigas do `aresta_app`.

### 5. Mecanismo de Migrações "Database-Only" (`AFETA_VERSAO_SERVING = False`)

Atualmente, `serving/update_serving.py` infere a versão da API do catálogo para o app (`kDataVersion`) calculando `max(num)` sobre todos os arquivos `.py` em `migracoes/`.
Para permitir que o repositório realize migrações de dados internos sem forçar um bump na versão de serving do app (`v4`), introduzimos a flag declarativa:
```python
# Em migracoes/0005_migrar_uids_e_rotulos.py:
AFETA_VERSAO_SERVING: bool = False
```
Em `serving/update_serving.py`, `get_db_version()` é atualizado para verificar se cada arquivo de migração define `AFETA_VERSAO_SERVING = False`. Migrações restritas ao database não incrementam `db_version`, mantendo o serving de produção em `v4`.
A política de migrações (`docs/politica_migracoes.md`) é atualizada para formalizar essa diretriz.

### 6. Script Automático de Migração `0005_migrar_uids_e_rotulos.py`

O script sequencial é posicionado em `migracoes/0005_migrar_uids_e_rotulos.py`:
- Invocado automaticamente pelo motor de migração (`aplicar_migracoes(caminho_db)`) ao carregar croquis experimentais no editor ou via `scripts/migrar_banco.py`.
- Atribui NanoIDs Base62 12c para todas as entidades e POIs de mapas que não possuam `uid`.
- Popula `ids_entidades.yaml` (`entidade_id_numerico`) e `ids_pontos.yaml` (`ponto_id_numerico`) mapeando UIDs para os IDs existentes.
- Converte referências de mapas para `alvo_uid` e `pontos_uids`, eliminando `escalada`, `setor`, `grupo`.
- Renomeia `label` para `rotulo`.
- Preserva comentários e formatação usando `ruamel.yaml`.

### 7. Refatoração do Editor Desktop (`editor/`)

O editor desktop é refatorado para operar exclusivamente com a nova arquitetura:
1. **Geração de UIDs**: Ao instanciar novos setores, grupos, escaladas ou POIs, gera automaticamente um NanoID Base62 12c formatado.
2. **Serialização Limpa**: `CroquiModel` e as rotinas de persistência gravam apenas `uid` nas entidades e `rotulo` nos POIs, sem emitir `id` direto nos `.md`/`.yaml`.
3. **Mapeamento de Traçados**: Os controladores e comandos de mapas manipulam `alvo_uid` e `pontos_uids`.
4. **Simplificação de Undo/Redo**: Comandos como `CmdRenomearEscalada` alteram unicamente a propriedade `nome` da via selecionada, descartando rotinas de sincronização em lote sobre arquivos de mapa.
5. **Carga Segura de Croquis Experimentais**: `JanelaPrincipal.carregar_croqui` executa `aplicar_migracoes` antes de ler o `croqui.yaml`, assegurando que qualquer croqui experimental legado seja atualizado automaticamente.

### 8. Testes de Contrato Arquiteturais

Para garantir que o repositório nunca regrida para referências legadas:
1. **Contrato do `database/`** (`tests/contrato_database_uids_test.py`):
   - Varre todos os arquivos `.md` e `croqui.yaml` do acervo.
   - Asserta que nenhuma entidade possui `id:` direto (permitido somente nos arquivos `ids_*.yaml`).
   - Asserta que nenhuma referência de mapa possui `escalada:`, `setor:` ou `grupo:`.
   - Asserta que nenhum POI possui `label:` (obrigatório `rotulo:`).
2. **Contrato do Editor**:
   - Testa a serialização de novos croquis e modificações, assegurando que o editor não gera arquivos contendo os campos legados.

### 9. Biblioteca Autônoma `scripts/gerenciar_ids_numericos_lib.py`

Biblioteca independente, pura e orientada a arquivos de texto:
1. `gerar_uid() -> str` e `validar_uid(uid: str) -> bool`.
2. Classes `TabelaIdsLocais` e `TabelaIdsGlobais` para alocação de IDs inteiros livres (`alocar_ou_obter_id(uid)`).
3. **Resolução Semântica de Conflitos de Merge (Técnica de Split de Visões)**:
   - Se o arquivo contiver marcadores de conflito (`<<<<<<< HEAD` ... `=======` ... `>>>>>>>`), a biblioteca gera em memória duas versões textuais completas (a visão HEAD e a visão Conflitante).
   - Ambas são carregadas via `yaml.safe_load()`.
   - As entradas da visão HEAD são mantidas intactas com seus IDs oficiais.
   - Entradas com UIDs novos da visão Conflitante são anexadas ao final com inteiros livres.
   - O arquivo é regravado limpo, resolvendo o conflito sem qualquer dependência de comandos do Git.

### 10. Pipeline de Compilação e Omissão de UIDs (`deploy_generated.py`)

No `deploy_generated.py`:
1. Sincroniza todas as entidades e POIs com as tabelas de mapeamento nos três níveis (`ids_globais.yaml`, `ids_entidades.yaml`, `ids_pontos.yaml`). Se faltar ID para algum UID, aloca e regrava.
2. Na serialização para `compilado.binarypb`:
   - Preenche os IDs numéricos inteiros:
     - Nível 1: `Croqui.croqui_id_numerico`
     - Nível 2: `Escalada.id`, `Setor.id`, `Grupo.id` e `Referencia.alvo_id` (`entidade_id_numerico`)
     - Nível 3: `Referencia.pontos_ids` (`ponto_id_numerico`)
   - **Omite os UIDs** para economizar bytes e garantir downloads offline ultraleves.
   - Popula as strings legadas (`escalada`, `setor`, `grupo` e `label`) em memória para retrocompatibilidade com clientes antigos.

## Risks / Trade-offs

| Risco Identificado | Severidade | Mitigação |
| :--- | :--- | :--- |
| **Incremento indevido de versão do serving** | Alta | `serving/update_serving.py` é atualizado para ignorar migrações com `AFETA_VERSAO_SERVING = False`. A versão de serving permanece fixa em `v4`. |
| **Conflito de merge em `ids_entidades.yaml` ou `ids_pontos.yaml`** | Média | A biblioteca `gerenciar_ids_numericos_lib` resolve automaticamente o conflito via split de visões, preservando a base oficial e appendando novas entidades. Nenhum arquivo `.md` precisa ser modificado. |
| **Sobrecarga de UIDs no download do app** | Média | Os campos `uid` são estritamente omitidos do `compilado.binarypb` gerado para o app, mantendo o consumo de disco mínimo. |
| **Incompatibilidade com apps antigos** | Alta | O compilador popula os campos legados `escalada`, `setor`, `grupo` e `label` no `.binarypb`, garantindo funcionamento normal de clientes legados. |
| **Regressão no editor ao salvar campos legados** | Alta | Testes de contrato arquiteturais validam tanto o conteúdo de `database/` quanto a saída do serializador do editor no CI. |

## Migration Plan

1. **Recompilação de Protobufs**: Executar `python build.py` atualizando os stubs `croqui_pb2.py`, `indice_pb2.py` e `croqui_experimental_pb2.py` (sem contadores de sequência).
2. **Suporte a Migrações Database-Only**: Atualizar `serving/update_serving.py` e `docs/politica_migracoes.md` com testes em `serving/update_serving_test.py`.
3. **Biblioteca de IDs nos Três Níveis**: Implementar `scripts/gerenciar_ids_numericos_lib.py` com 100% de cobertura de testes.
4. **Script de Migração Automática**: Implementar `migracoes/0005_migrar_uids_e_rotulos.py` (com `AFETA_VERSAO_SERVING = False`) e migrar todo o acervo do `database/`.
5. **Refatoração do Editor**: Atualizar modelos, controladores e comandos para operarem com UIDs, `rotulo` e invocarem migrações automáticas ao abrir croquis.
6. **Testes de Contrato**: Implementar `tests/contrato_database_uids_test.py` verificando a base de dados e a serialização do editor.
7. **Compilação e Deploy**: Integrar `gerenciar_ids_numericos_lib` em `deploy_generated.py` e `preparar_submissao_lib.py`.
8. **Validação Final**: Executar compilação completa do banco e suíte `pytest` garantindo 100% de cobertura.
