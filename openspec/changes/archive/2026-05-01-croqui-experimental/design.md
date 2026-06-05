## Context

Atualmente o Aresta lida com croquis dentro do repositório `aresta_db` estruturado e versionado via Git. Para permitir que o Aresta Editor (desktop) funcione como uma ferramenta local e offline, os croquis criados pelo usuário não devem impactar diretamente a base do repositório antes de estarem prontos. A proposta estabelece um formato de "Croqui Experimental", salvo no local storage do usuário e auto-contido.

## Goals / Non-Goals

**Goals:**
- Prover um formato auto-contido para edição de um único croqui com as mesmas ferramentas de compilação da base principal.
- Utilizar controle de versão (Git local) na pasta do croqui experimental.
- Permitir a exportação e importação de croquis experimentais na forma de um arquivo compacto `.croqui`.

**Non-Goals:**
- Sincronização direta destes repositórios com o GitHub (os repositórios são estritamente locais).
- Alterar o pipeline principal do `aresta_db` para lidar com a compilação do Aresta.

## Decisions

1. **Estrutura de Pastas Auto-contida:**
   A pasta do croqui terá metadados `croqui_experimental.yaml`, além das subpastas `database/` e `compilado/`. Isso reaproveita a lógica de compilação existente e mantém clara a separação entre o código-fonte gerado pelo autor e os dados lidos pelo app.

2. **Repositório Git Local (`.git`):**
   A pasta raiz de cada croqui experimental será um repositório git isolado. Isso permite que o sistema ofereça opções de "desfazer", histórico de alterações ou diffs antes do usuário exportar seu trabalho, seguindo o padrão TDD e rastreamento local confiável.

3. **Formato `.croqui` (ZIP):**
   A exportação do croqui compactará o diretório todo (incluindo o `.git`) em um arquivo zip com a extensão `.croqui`. A importação reverte o processo, descompactando na pasta `croquis_experimentais`. Caso a pasta já exista dentro de `croquis_experimentais`, é necessário adicionar um sufixo para que não substituia o croqui experimental já existente.

## Risks / Trade-offs

- **Tamanho do repositório local:** Imagens (binários) armazenados no `.git` sem LFS podem inflar o disco com o tempo.
  *Mitigação:* Como croquis tratam-se de escopos fechados, e as resoluções de imagens têm seus limites para o app mobile, o impacto será mitigado naturalmente pelo controle do usuário de seus croquis experimentais ativos.
