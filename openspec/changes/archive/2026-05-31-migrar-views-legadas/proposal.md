## Why

A pasta `views` deve conter apenas componentes visuais aderentes ao padrão MVC estrito (visões puras, que interagem apenas com Models ou delegam ações a Controllers). Atualmente, a pasta contém arquivos que operam como "God Objects", quebrando essa arquitetura ao interagir diretamente com Storage, banco de dados e rotinas do Core (como workers e servidores locais). Mover essas classes para `legacy_views` clarifica a fronteira arquitetural e protege o padrão adotado para novos desenvolvimentos.

## What Changes

- Mover os arquivos `area_principal.py`, `tela_de_carregamento.py`, `dialogo_busca_croqui.py`, e `dialogo_conexao_celular.py` da pasta `editor/views` para `editor/legacy_views`.
- Mover os arquivos de teste correspondentes (`*_test.py`) para acompanhar as views movidas.
- Atualizar os imports em todo o projeto (ex: `main.py`, testes de integração) para apontar para `editor.legacy_views.*` em vez de `editor.views.*`.

## Capabilities

### New Capabilities
<!-- Nenhuma nova funcionalidade exigida. Esta é uma mudança arquitetural/estrutural. -->

### Modified Capabilities
<!-- Não há mudança nos requisitos de negócio ou capacidades da aplicação, apenas na organização do código (Refatoração). -->

## Impact

- **Código Afetado**: `main.py` e quaisquer outros arquivos que importem essas views, além de seus respectivos arquivos de teste.
- **Riscos**: Podem ocorrer erros de importação (`ImportError`) ou testes quebrados se as referências cruzadas não forem corrigidas adequadamente após a movimentação dos arquivos.
