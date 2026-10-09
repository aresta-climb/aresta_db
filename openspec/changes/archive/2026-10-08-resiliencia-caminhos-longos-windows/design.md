# Design

## Context

Conforme estabelecido em `proposal.md`, o Windows impõe o limite `MAX_PATH` de 260 caracteres para APIs Win32 convencionais quando a chave de sistema `LongPathsEnabled` está desativada no registro do Windows (padrão em instalações de usuários finais). O pacote MSIX do Editor Aresta virtualiza o armazenamento de dados do usuário em `C:\Users\<user>\AppData\Local\Packages\...\LocalCache\Roaming\Editor Aresta (Beta)\`, consumindo aproximadamente 120 caracteres apenas no prefixo base.

Experimentos demonstraram que o motor gráfico do Qt (PySide6) rejeita caminhos no formato estendido Win32 (`\\?\`), tornando `QImage` e `QPixmap` nulos. Portanto, a solução deve manter os caminhos dentro do orçamento seguro de 260 caracteres para componentes visuais e isolar o manuseio de caminhos estendidos na biblioteca multiplataforma `editor.plataforma`, utilizada apenas em rotinas de build e I/O de baixo nível.

## Goals / Non-Goals

**Goals:**
- Garantir matematicamente que nenhum arquivo de imagem ou anexo importado no editor ultrapasse o teto de caracteres que causaria estouro de 260 caracteres no caminho absoluto.
- Eliminar o aninhamento redundante de subpastas do croqui na compilação do `ExperimentalWorkspace`.
- Encapsular a normalização de caminhos estendidos (`\\?\`) no protocolo `AdaptadorPlataforma` em `editor/plataforma/`, provendo implementação limpa para Windows, Linux e macOS.
- Tornar o `scripts/deploy_generated.py` resiliente a caminhos longos através do consumo da biblioteca `editor.plataforma`.
- Blindar a telemetria do Sentry em `editor/core/telemetria.py` para sanitizar caminhos representados com barras invertidas duplas (`\\`).
- Preservar 100% de cobertura de testes unitários e respeito aos Princípios de Engenharia Aresta.

**Non-Goals:**
- Criar camadas de abstração proprietárias de I/O em todo o repositório ou proibir primitivas nativas do Python (`open`, `Path`).
- Expor caminhos iniciados por `\\?\` para o Qt ou widgets de interface gráfica.
- Renomear ou quebrar retrocompatibilidade com croquis já compilados que possuam nomes de imagens existentes.

## Decisions

### 1. Teto de 40 Caracteres para Troncos de Nomes de Imagens e Anexos
- **Decisão**: Em `sanitizar_nome_imagem` (`editor/core/imagens_markdown.py`) e `sanitizar_nome_arquivo_anexo` (`editor/views/dialogos/dialogo_inserir_botao_markdown.py`), o tronco sanitizado (*stem*) será truncado em no máximo 40 caracteres (`nome_limpo[:40].rstrip("_")`).
- **Racional**: Com no máximo 40 caracteres no tronco, o arquivo final com sufixos de desambiguação (ex: `_99.webp`) terá no máximo ~48 caracteres. Somado aos ~120 caracteres da raiz MSIX e aos ~34 caracteres da pasta interna do croqui, o caminho absoluto total máximo atinge ~202 caracteres, garantindo uma folga de segurança de quase 60 caracteres abaixo do limite de 260.
- **Alternativas consideradas**: Permitir nomes de comprimento livre e tentar resolver via atalhos/symlinks no sistema de arquivos (complexo, frágil e dependente de privilégios de administrador no Windows).

### 2. Compactação da Saída no Workspace Experimental
- **Decisão**: No `ExperimentalWorkspace`, a compilação local gerará seus arquivos diretamente sob `compilado/` (ex: `compilado/imagens/` e `compilado/compilado.binarypb`), sem a subpasta intermediária `<croqui_id>/`.
- **Racional**: No repositório central `aresta_db`, a pasta `generated/` contém dezenas de croquis e necessita da subpasta `<croqui_id>`. No workspace experimental, a raiz já é dedicada exclusivamente àquele croqui (`croquis/<hash>/`), tornando a subpasta `<croqui_id>` uma redundância que consome entre 30 e 50 caracteres do caminho.
- **Alternativas consideradas**: Manter a subpasta `<croqui_id>` e apenas confiar no teto de 40 caracteres (reduziria a margem de folga desnecessariamente).

### 3. Normalização de Caminhos Estendidos na Biblioteca `editor.plataforma`
- **Decisão**: Adicionar o método `normalizar_caminho_estendido(self, caminho: Path | str) -> str` no protocolo `AdaptadorPlataforma` (`editor/plataforma/contrato.py`):
  - No `AdaptadorWindows` (`editor/plataforma/windows/integracao.py`): resolve o caminho para absoluto e adiciona o prefixo `\\?\` caso não esteja presente.
  - No `AdaptadorLinux` e `AdaptadorMacOS`: resolve o caminho para absoluto e retorna sua representação em string inalterada.
  - Na fachada `editor/plataforma/__init__.py`: expõe a função pública `normalizar_caminho_estendido(caminho: Path | str) -> str`.
- **Racional**: Centraliza qualquer regra de caminhos dependente de sistema operacional dentro do módulo `editor/plataforma`, respeitando o Princípio II (Library-First) e mantendo scripts como `deploy_generated.py` totalmente desacoplados de sintaxes específicas do Win32.
- **Alternativas consideradas**: Implementar helper solto diretamente dentro de `deploy_generated.py` (violaria a coesão da biblioteca de plataforma).

### 4. Sanitização de Barras Duplas no Sentry
- **Decisão**: Em `_obter_mapeamento_sanitizacao()` (`editor/core/telemetria.py`), adicionar mapeamento explícito para as versões com barras duplas escapadas (`caminho_original.replace("/", "\\").replace("\\", "\\\\")`).
- **Racional**: Erros do `shutil` e coleções Python serializam caminhos usando `repr()`, duplicando as barras invertidas. A inclusão dessa variante garante substituição precisa sem deixar escapar nomes de usuários em relatórios de falha.

## Risks / Trade-offs

- **[Risco] Nomes de imagens cortados podem perder informação semântica do arquivo original**  
  → *Mitigação*: No modelo do Aresta Climb, legendas, títulos, créditos e descrições são mantidos integralmente no corpo do Markdown (`![Legenda Completa](imagens/slug_curto.webp)`). O nome do arquivo atua estritamente como chave de armazenamento.

- **[Risco] Croquis existentes com nomes longos ao serem compilados**  
  → *Mitigação*: A normalização com `\\?\` via `editor.plataforma` no `deploy_generated.py` assegura que mesmo imagens antigas que ultrapassem o limite de 260 caracteres no destino sejam copiadas sem erro de `WinError 3`.
