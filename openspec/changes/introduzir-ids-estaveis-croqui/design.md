# Technical Design: Introduzir IDs Estáveis Universais com Pure NanoID 14c

## Context

O Aresta Climb utiliza Protobuf Edition 2023 (`croqui.proto` e `indice.proto`) para serialização de croquis e catálogos. O armazenamento-fonte no Git (`database/`) utiliza arquivos YAML (`croqui.yaml`) e Markdown com YAML Frontmatter (`grupo_*.md`, `setor_*.md`).

Historicamente, as conexões entre mapas visuais e dados eram mantidas através de triplas textuais `(grupo, setor, escalada)` em `Mapa.Referencia`. Esse acoplamento gerava extrema fragilidade: renomear uma via ou alterar sua estrutura exigia caçar e reescrever referências em múltiplos arquivos de mapas, além de lentidão na resolução de entidades.

Com a introdução da arquitetura de sincronização offline-first (PowerSync + Supabase) e links físicos permanentes (placas de aço inoxidável gravadas a laser nas falésias), há a necessidade imperativa de identificadores estáveis, imutáveis e universais.

Ao invés de adotar uma camada intermediária de tabelas de mapeamento em YAML (`ids_*.yaml`) e conversão para inteiros de 4 bytes (o que geraria dezenas de arquivos extras, risco de conflitos de merge de IDs no Git e necessidade de ferramentas complexas de resolução de split de visões), adotamos a arquitetura **Pure NanoID 14c Universal**:
- Um único identificador imutável de 14 caracteres em Base62 (`[0-9a-zA-Z]`, ex: `x8siJek3FiG3aB`).
- Atribuído universalmente para `Croqui`, `Grupo`, `Setor`, `Escalada` e `PontoDeInteresse` de mapas.
- Sem tabelas intermediárias de mapeamento em YAML e com risco nulo de colisão ou conflito de merge.
- URL física canônica ultra-curta: `https://aresta.cc/<uid>` (32 caracteres).
- Placas físicas gravadas com QR Code Versão 3 (29x29) Nível H (30% de tolerância a danos por sol, arranhão ou pó de magnésio).
- Serialização direta de `uid`, `alvo_uid` e `pontos_uids` no `compilado.binarypb`, preenchendo campos legados em memória para retrocompatibilidade com clientes antigos do app.
- Suporte a migrações "database-only" (`AFETA_VERSAO_SERVING = False`), mantendo a versão de serving do app inalterada em `v4`.

## Goals / Non-Goals

**Goals:**
- Atribuir NanoIDs 14c Base62 (`^[0-9a-zA-Z]{14}$`) universais e permanentes para todas as entidades (`Croqui`, `Grupo`, `Setor`, `Escalada` e `PontoDeInteresse`) no `database/` e no Protobuf.
- Desacoplar referências em mapas, adotando exclusivamente `alvo_uid` e `pontos_uids` no banco fonte e no compilado, deletando os campos textuais `escalada`, `setor` e `grupo` dos arquivos `.md` do `database/`.
- Substituir o termo `label` por `rotulo` (em português brasileiro) no Protobuf e nos arquivos fontes.
- Padronizar links e placas físicas com o domínio encurtador `https://aresta.cc/<uid>` e QR Code Versão 3 (29x29) Nível H (30% de tolerância a danos).
- Implementar a biblioteca pura e independente `scripts/gerenciar_uids_lib.py` (com 100% de cobertura de testes).
- Criar suporte a migrações "database-only" (`AFETA_VERSAO_SERVING = False`) para permitir evoluir dados internos e croquis experimentais sem alterar o serving de produção (`kDataVersion` permanece 4).
- Implementar o script de migração automática `migracoes/0005_migrar_uids_e_rotulos.py` para croquis experimentais e acervo.
- Refatorar o editor desktop para produzir e manipular nativamente NanoIDs 14c, `rotulo` e referências relacionais sem campos depreciados.
- Implementar testes de contrato rigorosos garantindo que nem a pasta `database/` nem o editor contenham ou emitam campos legados (`escalada`/`setor`/`grupo` em referências, `label:`, ou ausência de `uid:`).
- Serializar o `uid` diretamente no `compilado.binarypb` e preencher strings legadas em memória durante o build para garantir retrocompatibilidade total com clientes antigos do aplicativo móvel.

**Non-Goals:**
- Não criar tabelas ou arquivos intermediários de mapeamento em YAML (`ids_globais.yaml`, `ids_entidades.yaml`, `ids_pontos.yaml`).
- Não converter UIDs para inteiros numéricos (o NanoID 14c é o identificador definitivo em todo o ciclo de vida).
- Não implementar algoritmos de resolução de conflitos de merge de IDs (o espaço amostral de $1{,}24 \times 10^{25}$ torna o risco de colisão matematicamente desprezível).
- Não forçar dependência do binário Git em tempo de execução para compilação ou deploy.
- Não incrementar o serving do app para `v5` (a compatibilidade do binário compilado com `v4` é mantida integralmente).
- Não implementar o pré-download global de compilados sem mídia nesta change (o usuário definiu que isso será tratado em um follow-up futuro).

## Decisions

### 1. Pure NanoID 14c Base62 Universal (`[0-9a-zA-Z]`)

- Toda entidade (`Croqui`, `Grupo`, `Setor`, `Escalada` e `PontoDeInteresse`) recebe um identificador único universal de 14 caracteres em Base62 contínuo, sem separadores (ex: `x8siJek3FiG3aB`).
- **Espaço Amostral**: $62^{14} \approx 1{,}24 \times 10^{25}$ combinações.
- **Probabilidade de Colisão**: Pela fórmula do Paradoxo do Aniversário:
  $$P(\text{colisão}) \approx \frac{N^2}{2 \times S}$$
  Para $N = 1.000.000$ (um milhão de entidades escaláveis no planeta):
  $$P \approx \frac{10^{12}}{2{,}48 \times 10^{25}} \approx 4 \times 10^{-14} \quad (\approx 1 \text{ chance em } 25 \text{ trilhões})$$
  Mesmo com dezenas de milhares de autores trabalhando em forks desconectados, a colisão é impossível na prática.
- **Eliminação de Tabelas de Mapeamento**: Descarta completamente `ids_globais.yaml`, `ids_entidades.yaml` e `ids_pontos.yaml`. O UID reside unicamente no cabeçalho do arquivo fonte de cada entidade.
- **Adequação a Offline-First e PowerSync**: Bancos sincronizados como PowerSync e SQLite operam de maneira ideal com identificadores de texto gerados no cliente (NanoID/UUID), evitando gargalos com sequenciadores e auto-incrementos centralizados.

### 2. Domínio Encurtador `aresta.cc` e Física do QR Code nas Falésias

Para placas físicas de aço inoxidável fixadas na rocha sujeitas a intempéries por mais de 30 anos:
- **URL Canônica**: `https://aresta.cc/<uid>`
  - Exemplo: `https://aresta.cc/x8siJek3FiG3aB`
  - Tamanho exato: **32 caracteres**
- **Dimensionamento do QR Code**:
  - **Versão 3** (matriz de 29x29 módulos).
  - **Nível H** de correção de erro Reed-Solomon (30% de tolerância a perda de dados).
  - Capacidade da Versão 3 no Nível H em modo binário/alfanumérico: **até 35 caracteres**.
  - Os 32 caracteres cabem perfeitamente dentro dos limites da Versão 3 Nível H com 3 caracteres de folga.
- **Resiliência Física**: O nível de correção H permite que a placa sofra arranhões profundos de mosquetões, impregnação de pó de magnésio, oxidação superficial ou sujeira cobrindo quase 1/3 do código sem impedir a leitura pela câmera do smartphone.

```text
Placa de Aço Inox (Falésia)
┌──────────────────────────────────────┐
│  ARESTA CLIMB                        │
│  Via: Faca na Caveira - 8a           │
│                                      │
│  ┌─────────┐   https://aresta.cc/    │
│  │ █ ▄ █ ▄ │   x8siJek3FiG3aB        │
│  │ ▄ █ ▄ █ │                         │
│  │ █ ▄ █ ▄ │   QR Code Versão 3      │
│  └─────────┘   Correção Nível H (30%)│
└──────────────────────────────────────┘
```

### 3. Desacoplamento Relacional de Mapas

- No `database/`, as referências passam a ser puramente relacionais via UIDs:
  ```yaml
  referencias:
  - alvo_uid: "x8siJek3FiG3aB"
    pontos_uids:
    - "m7Kv9TwR48aB12"
    - "p9Ab8CxY34cD56"
  ```
- **Eliminação Definitiva de Strings Textuais**: Os campos `escalada`, `setor` e `grupo` são deletados dos arquivos Markdown de mapas. Renomear uma via torna-se uma edição pontual de 1 linha no atributo `nome` daquela via. O comando `CmdRenomearEscalada` no editor não precisa inspecionar nem atualizar mapas.
- No Protobuf, `escalada`, `setor` e `grupo` são marcados como `[deprecated = true]`.

### 4. Adoção do Termo `rotulo` em `PontoDeInteresse`

- Substituição de `label` por `rotulo` no Protobuf:
  ```protobuf
  string rotulo = 12 [(aresta.texto_na_ui) = "Rótulo na Imagem"];
  string label = 2 [deprecated = true];
  ```
- No `database/`, todos os campos `label:` são migrados para `rotulo:`.
- O compilador preenche tanto `rotulo` quanto `label` no `.binarypb` para garantir retrocompatibilidade com clientes legados.

### 5. Mecanismo de Migrações "Database-Only" (`AFETA_VERSAO_SERVING = False`)

Para permitir que o repositório realize migrações de dados internos sem forçar um incremento desnecessário na versão de serving do app (`v4`), introduzimos a flag declarativa:
```python
# Em migracoes/0005_migrar_uids_e_rotulos.py:
AFETA_VERSAO_SERVING: bool = False
```
Em `serving/update_serving.py`, `get_db_version()` é atualizado para verificar se cada arquivo de migração define `AFETA_VERSAO_SERVING = False`. Migrações restritas ao database não incrementam `db_version`, mantendo o serving de produção fixo em `v4`.
A política de migrações (`docs/politica_migracoes.md`) é atualizada para formalizar essa diretriz.

### 6. Script Automático de Migração `0005_migrar_uids_e_rotulos.py`

O script sequencial é posicionado em `migracoes/0005_migrar_uids_e_rotulos.py`:
- Invocado automaticamente pelo motor de migração (`aplicar_migracoes(caminho_db)`) ao carregar croquis experimentais no editor ou via `scripts/migrar_banco.py`.
- Atribui NanoIDs 14c Base62 para todas as entidades e POIs de mapas que não possuam `uid`.
- Converte referências de mapas para `alvo_uid` e `pontos_uids`, eliminando `escalada`, `setor`, `grupo`.
- Renomeia `label` para `rotulo`.
- Não cria nenhuma tabela intermediária YAML.
- Preserva comentários e formatação usando `ruamel.yaml`.

### 7. Refatoração do Editor Desktop (`editor/`)

O editor desktop é refatorado para operar exclusivamente com a nova arquitetura:
1. **Geração de UIDs**: Ao instanciar novos setores, grupos, escaladas ou POIs, gera automaticamente um NanoID 14c Base62.
2. **Serialização Limpa**: `CroquiModel` e as rotinas de persistência gravam apenas `uid` nas entidades e `rotulo` nos POIs, sem emitir campos depreciados.
3. **Mapeamento de Traçados**: Os controladores e comandos de mapas manipulam `alvo_uid` e `pontos_uids`.
4. **Simplificação de Undo/Redo**: Comandos como `CmdRenomearEscalada` alteram unicamente a propriedade `nome` da via selecionada, descartando rotinas de sincronização em lote sobre arquivos de mapa.
5. **Carga Segura de Croquis Experimentais**: `JanelaPrincipal.carregar_croqui` executa `aplicar_migracoes` antes de ler o `croqui.yaml`, assegurando que qualquer croqui experimental legado seja atualizado automaticamente.

### 8. Testes de Contrato Arquiteturais

Para garantir que o repositório nunca regrida para referências legadas:
1. **Contrato do `database/`** (`tests/contrato_database_uids_test.py`):
   - Varre todos os arquivos `.md` e `croqui.yaml` do acervo.
   - Asserta que toda entidade possui `uid:` de 14 caracteres Base62.
   - Asserta que nenhuma referência de mapa possui `escalada:`, `setor:` ou `grupo:`.
   - Asserta que nenhum POI possui `label:` (obrigatório `rotulo:`).
   - Asserta que não existem tabelas residuais `ids_*.yaml`.
2. **Contrato do Editor** (`tests/contrato_editor_serializacao_test.py`):
   - Testa a serialização de novos croquis e modificações, assegurando que o editor não gera arquivos contendo os campos legados.

### 9. Biblioteca Pura `scripts/gerenciar_uids_lib.py`

Biblioteca independente, pura e autossuficiente:
1. `gerar_uid() -> str`: Gera NanoID 14c Base62 criptograficamente seguro (`secrets.choice`).
2. `validar_uid(uid: str) -> bool`: Valida se a string atende a `^[0-9a-zA-Z]{14}$`.
3. `formatar_url_aresta(uid: str) -> str`: Retorna a URL canônica `https://aresta.cc/{uid}`.
4. `extrair_uid_de_url(url: str) -> str | None`: Faz parse seguro de links escaneados em placas físicas.

### 10. Pipeline de Compilação e Retrocompatibilidade (`deploy_generated.py`)

No `deploy_generated.py`:
1. Audita que todas as entidades e POIs possuem UIDs válidos de 14 caracteres.
2. Na serialização para `compilado.binarypb`:
   - Armazena diretamente os campos `uid`, `alvo_uid` e `pontos_uids`.
   - Popula em memória os campos legados (`escalada`, `setor`, `grupo` e `label`) para retrocompatibilidade com versões anteriores do `aresta_app`.
   - O serving permanece em `v4` sem afetar downloads já cacheados nos clientes.

## Risks / Trade-offs

| Risco Identificado | Severidade | Mitigação |
| :--- | :--- | :--- |
| **Incremento indevido de versão do serving** | Alta | `serving/update_serving.py` é atualizado para ignorar migrações com `AFETA_VERSAO_SERVING = False`. A versão de serving permanece fixa em `v4`. |
| **Colisão de UIDs entre autores concorrentes** | Nula | Espaço de $1{,}24 \times 10^{25}$ combinações garante probabilidade inferior a $10^{-13}$ para $10^6$ vias. |
| **Danos físicos em placas na rocha** | Alta | QR Code Versão 3 com correção Nível H (30% de tolerância a perda física de área por riscos, desgaste e magnésio) com a URL curta de 32 caracteres. |
| **Incompatibilidade com apps legados** | Alta | O compilador popula os campos legados `escalada`, `setor`, `grupo` e `label` em memória no `.binarypb`, garantindo funcionamento ininterrupto. |
| **Regressão no editor ao salvar campos legados** | Alta | Testes de contrato arquiteturais validam tanto o conteúdo de `database/` quanto a saída do serializador do editor no CI. |

## Migration Plan

1. **Modelagem Protobuf**: Atualizar `croqui.proto`, `indice.proto` e `croqui_experimental.proto` com campos `uid`, `rotulo`, `alvo_uid` e `pontos_uids`. Executar `python build.py` gerando stubs Python.
2. **Suporte a Migrações Database-Only**: Atualizar `serving/update_serving.py` e `docs/politica_migracoes.md` com testes em `serving/update_serving_test.py`.
3. **Biblioteca Pura de UIDs**: Implementar `scripts/gerenciar_uids_lib.py` com 100% de cobertura de testes em `scripts/gerenciar_uids_lib_test.py`.
4. **Script de Migração Automática**: Implementar `migracoes/0005_migrar_uids_e_rotulos.py` (com `AFETA_VERSAO_SERVING = False`) e migrar todo o acervo do `database/`.
5. **Refatoração do Editor Desktop**: Atualizar modelos, controladores e comandos para operarem com UIDs, `rotulo` e invocarem migrações automáticas ao abrir croquis experimentais.
6. **Testes de Contrato**: Implementar `tests/contrato_database_uids_test.py` e `tests/contrato_editor_serializacao_test.py` verificando a base de dados e a serialização do editor.
7. **Compilação e Deploy**: Integrar `gerenciar_uids_lib` em `deploy_generated.py` e `preparar_submissao_lib.py`, preenchendo campos legados em memória.
8. **Validação Final**: Executar compilação completa do banco e suíte `pytest` garantindo 100% de cobertura.
