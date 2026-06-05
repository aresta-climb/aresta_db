## Context

O Aresta Editor é uma aplicação desktop para edição de croquis de escalada, projetada para uso por contribuidores que não possuem ambiente de desenvolvimento. O aplicativo empacota o código em um executável fácil de instalar e usar.

Nesta primeira etapa da implementação, o objetivo é criar a fundação da aplicação desktop usando a biblioteca PyQt6 para a interface gráfica e o PyInstaller para empacotar tudo em binários auto-suficientes. A aplicação deve realizar a inicialização criando uma pasta em diretório local para armazenar os dados e o repositório clonado via git. Em seguida, deve exibir uma tela inicial dividida em duas partes: botões para abrir novos croquis ("Novo croqui", "Importar croqui experimental", "Editar croqui oficial") e uma lista de croquis experimentais recentes para continuar a edição.

## Goals / Non-Goals

**Goals:**
- Configurar o ambiente do subprojeto na pasta `editor`.
- Criar a interface principal em PyQt6 com a tela de boas-vindas contendo as opções "Novo croqui", "Importar croqui experimental" e "Editar croqui oficial", além de uma lista vazia de croquis recentes.
- Implementar a inicialização do diretório local (usando `QStandardPaths` do Qt) para armazenar os dados do app.
- Configurar os scripts de empacotamento com PyInstaller.

**Non-Goals:**
- Implementar a edição real e o formulário de arquivos `.croqui` (campos protobuf).
- Implementar as funcionalidades complexas de compilação ou transferência via servidor HTTP.
- Autenticação e automação do GitHub OAuth.
- Sistema complexo de auto-update (atualização silenciosa em background com notificação de reinício e checagem de envios).

## Decisions

- **Framework Gráfico**: `PyQt6`. Oferece boa integração nativa em múltiplas plataformas (Windows, macOS, Linux), estabilidade e uma vasta API em Python para interfaces ricas.
- **Gerenciamento de Pastas Locais**: `QStandardPaths.StandardLocation.AppDataLocation`. Deixa a cargo do Qt descobrir a pasta correta (`%APPDATA%` no Windows, `~/.local/share` ou `~/.config` no Linux, `~/Library/Application Support` no Mac).
- **Empacotamento**: PyInstaller no modo `--windowed` / `--noconsole` gerará executáveis nativos e isolados para cada OS.

## Risks / Trade-offs

- **Tamanho do Executável**: Binários com PyQt6 costumam passar de 50MB.
  - *Mitigação*: Será aceitável na primeira versão, pois a simplicidade de distribuição de um único `.exe` ou `.AppImage` compensa o tamanho do download para usuários de internet banda larga.