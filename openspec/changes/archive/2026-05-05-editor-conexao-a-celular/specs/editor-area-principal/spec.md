## MODIFIED Requirements

### Requirement: Barra de Ferramentas Superior (Top Toolbar)
A Top Toolbar SHALL conter ícones para ações globais, incluindo: Abrir novo croqui, Salvar, Desfazer, Refazer, Exportar, Conectar com Celular e Publicar.

#### Scenario: Interação com botão Publicar
- **WHEN** o usuário clica no botão "Publicar" na barra superior
- **THEN** o sistema SHALL:
    1. Verificar se há modificações não salvas (e solicitar salvamento se necessário)
    2. Abrir um diálogo para coletar título e descrição da contribuição
    3. Criar uma branch temporária, enviar as alterações para o fork do usuário e criar um Pull Request no GitHub

#### Scenario: Abrir novo croqui sem modificações
- **WHEN** o usuário clica em "Abrir novo croqui" E não há modificações pendentes
- **THEN** o sistema SHALL fechar a Janela Principal e retornar para a Tela de Carregamento

#### Scenario: Abrir novo croqui com modificações pendentes
- **WHEN** o usuário clica em "Abrir novo croqui" E há modificações não salvas
- **THEN** o sistema SHALL solicitar confirmação de salvamento antes de retornar para a Tela de Carregamento

#### Scenario: Interação com botão Salvar
- **WHEN** o usuário clica no botão "Salvar" na barra superior
- **THEN** o sistema SHALL:
    1. Persistir as alterações na pasta `database` do croqui experimental
    2. Gerar automaticamente os artefatos de saída na pasta `compilado`
    3. Realizar um commit no repositório git local

#### Scenario: Interação com botões Desfazer/Refazer
- **WHEN** o usuário clica em "Desfazer" ou "Refazer"
- **THEN** o sistema SHALL executar a ação correspondente no histórico de comandos do croqui

#### Scenario: Interação com botão Exportar
- **WHEN** o usuário clica no botão "Exportar" na barra superior
- **THEN** o sistema SHALL gerar o arquivo `.croqui` (ZIP) com os dados do croqui

#### Scenario: Interação com botão Celular (Inativo)
- **WHEN** a conexão com o celular está inativa (indicador vermelho)
- **AND** o usuário clica no botão "Celular"
- **THEN** o sistema SHALL iniciar o processo de conexão e abrir o diálogo de instruções

#### Scenario: Interação com botão Celular (Ativo)
- **WHEN** a conexão com o celular está ativa (indicador verde)
- **AND** o usuário clica no botão "Celular"
- **THEN** o sistema SHALL reabrir o diálogo de conexão com opção de encerrar
