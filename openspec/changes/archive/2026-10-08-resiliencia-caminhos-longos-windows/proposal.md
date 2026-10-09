# Proposal

## Why

No Windows, ambientes empacotados como MSIX utilizam caminhos base longos decorrentes da virtualização de diretórios (`LocalCache\Roaming`), o que, combinado com nomes descritivos de arquivos e pastas aninhadas no compilador, pode ultrapassar o limite histórico de 260 caracteres (`MAX_PATH`) da API Win32 do Windows. Além disso, exceções contendo listas ou tuplas com caminhos de arquivos (como `shutil.Error`) formatam separadores de diretório como barras invertidas duplas (`\\`), escapando do mecanismo atual de sanitização da telemetria e expondo nomes de usuários ao Sentry.

Esta mudança introduz uma estratégia em quatro camadas para eliminar de forma definitiva qualquer risco de estouro do limite `MAX_PATH` no ecossistema Windows sem quebrar a compatibilidade do motor gráfico do Qt (PySide6), e blinda a biblioteca de telemetria contra vazamentos de caminhos locais representados com barras duplas.

## What Changes

- **Limitação de Comprimento em Nomes de Imagens e Anexos**: As funções de sanitização (`sanitizar_nome_imagem` e `sanitizar_nome_arquivo_anexo`) passam a truncar o tronco (*stem*) do nome do arquivo em no máximo 40 caracteres, garantindo que o nome final gerado nunca ultrapasse ~48 caracteres mesmo com sufixos numéricos de desambiguação.
- **Simplificação Estrutural do Workspace Experimental**: No `ExperimentalWorkspace`, a compilação local deixa de aninhar redundantemente o `<croqui_id>` dentro da pasta `compilado/`, gravando diretamente os artefatos compilados e suas imagens na raiz de `compilado/`, economizando mais de 30 caracteres no orçamento de caminho.
- **Normalização de Caminho Estendido na Biblioteca de Plataforma**: A biblioteca `editor/plataforma/` (`AdaptadorPlataforma`, implementações e fachada) passa a prover o método `normalizar_caminho_estendido(caminho)` que, no Windows, prefixa caminhos absolutos com `\\?\`, e em Linux/macOS preserva a representação canônica pura, permitindo que primitivas de disco de baixo nível operem de forma agnóstica e imune a limites de caminho.
- **Resiliência a Caminhos Longos no Deploy (Win32)**: As rotinas de manipulação de disco em `scripts/deploy_generated.py` (`copiar_imagens`, `copiar_anexos` e `force_rmtree`) passam a consumir `normalizar_caminho_estendido` da plataforma antes de executar operações de sistema de arquivos (`shutil.copytree`, `shutil.rmtree`, etc.).
- **Sanitização de Barras Duplas na Telemetria**: A rotina `sanitizar_texto_caminhos` em `editor/core/telemetria.py` passa a detectar e substituir variações de caminhos contendo barras invertidas duplas (`\\`), assegurando que strings formatadas via `repr()` ou coleções de dados em exceções nunca vazem diretórios locais ou identidades de usuários.

## Capabilities

### Modified Capabilities
- `windows-long-path-support`: Expande os requisitos de suporte a caminhos longos no Windows para incluir normalização com prefixo `\\?\` via `editor/plataforma/` e redução de aninhamento no workspace experimental.
- `editor-markdown-imagens`: Adiciona a regra de truncamento e limite de tamanho máximo (40 caracteres no tronco) na sanitização de nomes de arquivos de imagem importados.
- `editor-inserir-botao-markdown`: Adiciona a regra de truncamento e limite de tamanho máximo (40 caracteres no tronco) na sanitização de nomes de arquivos anexos importados.
- `editor-telemetria-crash`: Estende a sanitização de PII para cobrir caminhos formatados com barras duplas escapadas (`\\`).

## Impact

- `editor/plataforma/contrato.py`, `editor/plataforma/__init__.py`, `editor/plataforma/windows/integracao.py`, `linux/` e `macos/`: Inclusão do método `normalizar_caminho_estendido`.
- `editor/core/imagens_markdown.py`: Adição de corte do slug em 40 caracteres em `sanitizar_nome_imagem`.
- `editor/views/dialogos/dialogo_inserir_botao_markdown.py`: Adição de corte do slug em 40 caracteres em `sanitizar_nome_arquivo_anexo`.
- `editor/core/workspace.py` e `editor/core/croqui_experimental.py`: Ajuste para apontar a saída compilada do workspace experimental sem o aninhamento redundante de `<croqui_id>`.
- `scripts/deploy_generated.py`: Consumo de `normalizar_caminho_estendido` para cópias e limpezas.
- `editor/core/telemetria.py`: Expansão do mapeamento de sanitização para abranger `\\`.
- Testes unitários de todas as bibliotecas afetadas mantendo 100% de cobertura.
