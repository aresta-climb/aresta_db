## 1. Setup do Projeto

- [ ] 1.1 Criar a pasta base `editor` na raiz do projeto
- [ ] 1.2 Configurar o ambiente do módulo (ex: arquivo de dependências) adicionando `PyQt6` e `pyinstaller`

## 2. Core Lógico de Inicialização

- [ ] 2.1 Criar módulo para descobrir ou criar a pasta de local storage usando `QStandardPaths` do PyQt6
- [ ] 2.2 Implementar estrutura inicial de subpastas (como `bin` e `croquis`) dentro do diretório de dados local no momento de inicialização

## 3. Interface Gráfica Inicial (PyQt6)

- [ ] 3.1 Criar classe da janela principal (`QMainWindow`) com tamanho padrão e título "Editor Aresta"
- [ ] 3.2 Implementar o layout esquerdo com os botões "Novo croqui", "Importar croqui experimental" e "Editar croqui oficial"
- [ ] 3.3 Implementar a visão direita para lista de "Croquis experimentais" vazia, com títulos e listagem inicial
- [ ] 3.4 Conectar inicialização da GUI ao arquivo principal de execução (`main.py` ou similar)

## 4. Empacotamento via PyInstaller

- [ ] 4.1 Criar script ou configuração de build configurando o PyInstaller com modo janela (`--windowed`/`--noconsole`)
- [ ] 4.2 Validar build testando geração do executável em ambiente local
