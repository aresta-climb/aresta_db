# Tasks: Distribuição Soberana do Editor Aresta via Repositório OSTree (Flatpak) no Cloudflare R2

## 1. Verificação Remota Ativa no Adaptador Linux (TDD)

- [x] 1.1 Criar testes unitários em `editor/plataforma/linux/integracao_test.py` cobrindo a consulta a `version.json` (versão mais recente opcional, versão mandatória, versão idêntica e resiliência a falhas de rede) e verificar que os testes falham inicialmente (Red).
- [x] 1.2 Implementar a consulta remota e mapeamento de `ResultadoAtualizacao` em `AdaptadorLinux.verificar_atualizacoes_disponiveis()` em `editor/plataforma/linux/integracao.py` e verificar que todos os testes passam com 100% de cobertura (Green).

## 2. Biblioteca de Release e Sincronização com Cloudflare R2 (Library-First & TDD)

- [x] 2.1 Criar testes unitários em `editor/release_tools/publicar_flatpak_r2_test.py` cobrindo a verificação HTTP segura do repositório remoto (sem `|| true`), geração de `version.json`, `.flatpakref` e `.flatpakrepo`, upload incremental via boto3 com headers uniformes e chamada da API de purge de cache da Cloudflare (Red).
- [x] 2.2 Implementar a biblioteca `editor/release_tools/publicar_flatpak_r2.py` com tipagem estática e tratamento robusto de erros, verificando que todos os testes unitários passam com 100% de cobertura (Green).

## 3. Workflow de CI/CD do GitHub Actions

- [x] 3.1 Atualizar `.github/workflows/build_editor_linux.yml` para importar a chave privada GPG dos segredos (`ARESTA_FLATPAK_GPG_PRIVATE_KEY`), configurar `flatpak-builder@v6` com `cache: true` e `build-bundle: false`, e integrar a chamada a `publicar_flatpak_r2.py`.
- [x] 3.2 Comentar a etapa de sincronização com o repositório Flathub (`aresta-editor-flathub`) e remover referências a bundles offline `.flatpak` em `.github/workflows/build_editor_linux.yml`.

## 4. Validação Integrada e Documentação

- [x] 4.1 Executar a suíte de testes completa do repositório (`pytest`) garantindo integridade global e ausência de regressões.
- [x] 4.2 Documentar no guia de distribuição as instruções de instalação para usuários Linux via `.flatpakref` e comandos de terminal.
