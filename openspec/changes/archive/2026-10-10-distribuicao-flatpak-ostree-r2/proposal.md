# Proposal: Distribuição Soberana do Editor Aresta via Repositório OSTree (Flatpak) no Cloudflare R2

## Why

A submissão do Editor Aresta ao Flathub encontra-se bloqueada por revisões com gatekeeping ideológico e arbitrário em relação ao uso de ferramentas de IA, apesar do projeto manter rigorosos padrões de engenharia com TDD e mais de 2.300 testes automatizados. O aplicativo necessita de um canal de distribuição estável e imediato para usuários Linux que preserve o isolamento em sandbox do Flatpak e, crucialmente, garanta que todos os usuários recebam atualizações automáticas assim que uma nova versão for publicada, sem depender de intermediários externos.

## What Changes

- **Repositório OSTree Soberano no R2**: Publicação do repositório Flatpak OSTree (modo `archive-z2`) hospedado em `https://serving.arestaclimb.com/flatpak/repo/`, assinado digitalmente com chave GPG oficial do projeto.
- **Distribuição Exclusiva com Auto-Update via `.flatpakref`**: Eliminação do bundle avulso offline `.flatpak`, disponibilizando a instalação exclusivamente por arquivo `.flatpakref` e remote `.flatpakrepo`, assegurando que 100% dos usuários Linux permaneçam no canal de atualização contínua.
- **Auto-Atualização Ativa no Aplicativo (In-App)**: Implementação no `AdaptadorLinux` da verificação ativa de versão remota através de `https://serving.arestaclimb.com/flatpak/version.json`, integrando com a `TelaDeAbertura` para notificar e orientar atualizações mandatórias.
- **Pipeline de Release e Cache Inteligente no CI**:
  - Configuração do `flatpak-builder@v6` com `cache: true` e `build-bundle: false` para acelerar compilações no GitHub Actions reaproveitando o cache de downloads e módulos compilados.
  - Sincronização incremental com Cloudflare R2 via script Python/boto3 com Cache-Control uniforme.
  - Purge automático de cache via API Cloudflare restrito aos arquivos de metadados mutáveis (`summary`, `summary.sig`, `version.json`, `com.arestaclimb.Editor.flatpakref`, `aresta.flatpakrepo`).
  - Verificação segura do repositório anterior sem mascaramento de erros com `|| true`.
- **Desacoplamento do Flathub**: Suspensão comentada do push para o repositório `aresta-editor-flathub` no workflow de release.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability durável isolada necessária; o comportamento de distribuição Linux existente é expandido e refinado -->

### Modified Capabilities
- `editor-distribuicao-linux`: Atualiza os requisitos de distribuição para substituir a dependência da rede Flathub e de bundles `.flatpak` avulsos pelo repositório OSTree soberano assinado com GPG no Cloudflare R2, integrando verificação ativa de versão na inicialização do aplicativo e instalador `.flatpakref` com `RuntimeRepo` apontado para runtimes públicos.

## Impact

- **Código do Editor**:
  - `editor/plataforma/linux/integracao.py`: Atualização do método `verificar_atualizacoes_disponiveis()` para consultar `version.json` e emitir status de atualização (disponível ou obrigatória).
- **Scripts de Release**:
  - Criação de ferramenta modular e testada em `editor/release_tools/publicar_flatpak_r2.py` para assinar o repositório, gerar metadados (`version.json`, `.flatpakref`, `.flatpakrepo`), sincronizar arquivos com R2 e acionar purge de cache na Cloudflare.
- **Workflows do GitHub Actions**:
  - `.github/workflows/build_editor_linux.yml`: Atualização do job para importar chave GPG, compilar com cache do `flatpak-builder`, publicar no R2 e comentar o sync com o Flathub.
- **Infraestrutura**:
  - Novo segredo do GitHub Actions `ARESTA_FLATPAK_GPG_PRIVATE_KEY` e inclusão do prefixo `flatpak/` no bucket R2 `aresta-serving`.
