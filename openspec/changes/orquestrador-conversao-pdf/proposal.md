## Why

Atualmente, o processo de conversão de um croqui em formato PDF para dados estruturados requer a execução manual e sequencial de três workflows diferentes (`preparacao_pdf_para_conversao`, `converter_pdf_para_croqui`, `extrair_informacoes_dos_mapas`). Isso gera uma alta carga cognitiva para o usuário, que precisa saber exatamente qual workflow rodar e em qual momento, gerenciando o estado mental da conversão.
A introdução do Antigravity 2.0 com suporte a sub-agentes permite que unifiquemos essas etapas em um único Agente Orquestrador. Esse agente gerenciará as transições, paralelizará o processamento pesado e pausará estrategicamente para validação humana.

## What Changes

- Criação de um novo workflow global que atua como o **Agente Orquestrador** (`/processar_croqui_completo.md`).
- O orquestrador gerenciará o estado de forma **implícita** (checa a presença de `partes.json`, arquivos `.md`, e json dos mapas) para permitir a retomada de processamento se for interrompido.
- Implementação de sub-agentes usando `define_subagent` para encapsular as lógicas especializadas (SeparadorPDF, ConversorMarkdown, ExtratorMapas).
- Execução maciça em paralelo com `invoke_subagent` (por exemplo, processar todos os setores ao mesmo tempo).
- Criação de um mecanismo de **Auto-correção (Auto-heal)** onde o Agente Principal captura o erro do sub-agente e reinicia um novo agente específico para consertar o erro antes de desistir e pedir ajuda.
- Inclusão de **Checkpoints** automáticos: o orquestrador para e pede a bênção humana após passos sensíveis (gerar arquivos de parte, compilar mapas).

## Capabilities

### New Capabilities
- `orquestrador-agentes-pdf`: A infraestrutura de prompt/instruções para que o orquestrador gerencie estado implícito, sub-agentes, paralelização e o loop de auto-heal.

### Modified Capabilities

## Impact

- Redução da complexidade para o usuário de converter PDFs (basta usar um workflow ao invés de três).
- Redução brusca do tempo de conversão pelo uso agressivo de `invoke_subagent` paralelo.
- Afeta diretamente como a CLI / sistema de workflows se comportam para as pastas de croquis novos, mas não altera a base de dados (`database`) nem a arquitetura das aplicações clientes (Editor ou Frontend).
