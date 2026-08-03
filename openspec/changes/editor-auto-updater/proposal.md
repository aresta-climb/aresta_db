## Why

Para blindar o ciclo de vida e a distribuição do Editor Aresta no Windows. O processo de distribuição manual de executáveis é passível de falha humana, resultando em desenvolvedores usando versões defasadas espalhadas em diretórios aleatórios. Ao prover um mecanismo de auto-instalação e atualização silenciosa na inicialização, garantimos que 100% da equipe utilize o build mais recente em um ambiente canônico previsível.

Alinhado com nossos princípios, esta fase será desenvolvida utilizando **TDD (Test-Driven Development)**, garantindo **100% de cobertura de testes unitários** e seguindo a abordagem **Library-First**. Toda a lógica do atualizador residirá em uma biblioteca autônoma e independente, sem sujar o `main.py` com lógica de negócios de infraestrutura.

## What Changes

- **Abordagem Library-First**: Criação de uma biblioteca dedicada (`lib/auto_updater`), totalmente testável e independente da interface gráfica (PyQt).
- **Test-Driven Development (TDD)**: Todos os componentes serão desenvolvidos sob o ciclo Red-Green-Refactor, com testes de integração e unitários escritos previamente.
- **Auto-Instalação Canônica**: Se o usuário executar o aplicativo de pastas não-oficiais (como Downloads ou Desktop), a biblioteca criará a pasta base em `%LOCALAPPDATA%\EditorAresta`, moverá a si mesma para lá e deixará um atalho (`.lnk`) na pasta de origem.
- **Gerenciamento de Lixo Seguro**: Processo de exclusão de binários velhos (`.old.exe`) estritamente limitado à pasta oficial e à pasta registrada num arquivo `cleanup_folder.txt`, prevenindo a possibilidade de exclusão de arquivos críticos.
- **Pré-Boot Updater**: Avaliação de versão via API do GitHub desacoplada do fluxo de Login da aplicação. Tentará capturar passivamente o Token do Keyring do Windows e realizará o request.
- **Update In-place (Rename Trick)**: Lógica para contornar o bloqueio de arquivo do Windows. O app baixa o arquivo, altera o próprio nome em execução, hospeda o novo `.exe` e reinicia.

## Capabilities

### New Capabilities
- `auto-install-cleanup`: Lógica de gerenciamento de disco, responsável por estabelecer o porto seguro (`AppData`) e limpar os resíduos (`.old.exe`), coberta por testes robustos e independentes.
- `boot-auto-updater`: Orquestração de requests, download via Github Releases e chamadas de Restart do OS, encapsulados em módulos testáveis.

### Modified Capabilities
- Inicialização do sistema no `main.py`, que agora delegará o pré-boot de atualização para a nova biblioteca.

## Impact

- Isolamento da complexidade no boot através de uma nova biblioteca `auto_updater`, mantendo a simplicidade do `main.py`.
- Instabilidade isolada tratada através de Fallbacks graciosos testados via Mocks (falhas de rede, permissões, etc).
- Excelente manutenibilidade devido à garantia de 100% de cobertura de código.
- Experiência fluida (UX) para o usuário, que se beneficia de uma ferramenta que se auto-mantém de forma invisível.
