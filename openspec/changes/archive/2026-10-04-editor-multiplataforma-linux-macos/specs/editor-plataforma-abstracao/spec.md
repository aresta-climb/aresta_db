## Purpose

Fornece uma biblioteca autossuficiente e desacoplada (`editor/plataforma/`) para isolamento de recursos dependentes do sistema operacional no Editor Aresta, assegurando conformidade com os Princípios de Engenharia Aresta através de interface agnóstica e testes de integração de fronteira estáticos.

## ADDED Requirements

### Requirement: Fachada Pública Agnóstica de Plataforma
O sistema DEVE (SHALL) expor uma interface pública e agnóstica de plataforma através da biblioteca `editor.plataforma` para serviços de integração com o sistema operacional, incluindo inicialização gráfica, notificação de atualizações e configurações de janela, com nomenclatura 100% em português brasileiro.

#### Scenario: Execução em plataforma suportada
- **WHEN** a aplicação é inicializada em Windows, Linux ou macOS
- **THEN** a fachada `editor.plataforma` resolve deterministicamente o adaptador de plataforma correspondente
- **AND** nenhum componente de visão ou controlador externo acessa diretamente submódulos específicos de sistema operacional

### Requirement: Isolamento Estrito de Dependências e Teste de Fronteiras AST
O sistema DEVE (SHALL) proibir a importação direta de módulos e bibliotecas nativas de sistema operacional (como `winrt`, `ctypes.windll`, `objc` ou chamadas diretas de subprocessos de SO) fora dos subdiretórios correspondentes em `editor/plataforma/`.

#### Scenario: Validação estática de importações proibidas
- **WHEN** o teste unitário de fronteiras de plataforma for executado
- **THEN** o analisador sintático (AST) percorre todos os arquivos `.py` do pacote `editor/`
- **AND** falha imediatamente se qualquer importação de biblioteca de plataforma for encontrada fora de `editor/plataforma/`
- **AND** falha se qualquer arquivo fora de `editor/plataforma/` importar diretamente de `editor.plataforma.windows`, `editor.plataforma.linux` ou `editor.plataforma.macos`

### Requirement: Diretório Canônico de Dados do Aplicativo por Plataforma
O sistema DEVE (SHALL) padronizar e isolar o diretório de dados do usuário (`EditorAresta`) respeitando as convenções oficiais de cada sistema operacional.

#### Scenario: Resolução do diretório no Linux
- **WHEN** o editor solicita o diretório base de armazenamento no Linux
- **THEN** o sistema resolve o caminho baseado em XDG Data Home (`~/.local/share/EditorAresta`)

#### Scenario: Resolução do diretório no macOS
- **WHEN** o editor solicita o diretório base de armazenamento no macOS
- **THEN** o sistema resolve o caminho em Application Support do usuário (`~/Library/Application Support/EditorAresta`)
