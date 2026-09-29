# Proposta: Detecção Automática de Fatiamento de Imagens em PDFs

## Why

PDFs diagramados em softwares como Canva, InDesign e Illustrator frequentemente utilizam *transparency flattening*, particionando fotos de fundo com sobreposições vetoriais ou textos em dezenas de fatias retangulares adjacentes (mosaicos). Atualmente, agentes e usuários precisavam identificar visualmente essa fragmentação e passar manualmente a flag `--incluir-paginas` no script `repartir_pdf.py`. A detecção automática resolve essa fragilidade na raiz, gerando automaticamente páginas inteiras (`pX.webp`) de alta resolução quando houver fatiamento e simplificando os fluxos e instruções dos agentes.

## What Changes

- **Detecção Automática de Fatiamento (Tiling)**: Implementação de algoritmo geométrico em `scripts/repartir_pdf.py` que inspeciona as imagens da página, identificando se há fatias adjacentes que compartilham bordas e cobrem a área da página/bloco.
- **Ativação Automática de Páginas Completas**: Quando detectado fatiamento em uma página/parte, ativa automaticamente a renderização da página completa em alta resolução (`pX.webp`), mesmo se a flag CLI `--incluir-paginas` não tiver sido passada.
- **Supressão Opcional/Limpeza de Fatias Quebradas**: Evita poluir o diretório com dezenas de recortes parciais inúteis para páginas onde o fatiamento foi detectado e a página completa foi renderizada.
- **Simplificação de Workflows e Skills**:
  - Remove a necessidade de instruir o agente a passar `--incluir-paginas` manualmente em `.agents/workflows/processar_croqui_completo.md`.
  - Atualiza `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md` e `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md` para refletir o comportamento automático.
- **100% de Cobertura de Testes Unitários**: Testes unitários dedicados em `scripts/repartir_pdf_test.py` cobrindo cenários com fatiamento, sem fatiamento, adjacências e flags explícitas.

## Capabilities

### New Capabilities
- `extracao-imagens-pdf`: Detecção determinística de mosaicos de imagens decorrentes de achatamento de transparências em PDFs e extração inteligente da página íntegra.

### Modified Capabilities
<!-- Nenhuma especificação existente teve seus requisitos alterados. -->

## Impact

- Código afetado:
  - `scripts/repartir_pdf.py`
  - `scripts/repartir_pdf_test.py`
- Documentação e agentes afetados:
  - `.agents/workflows/processar_croqui_completo.md`
  - `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md`
  - `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md`
- Nenhuma quebra de retrocompatibilidade com croquis já compilados ou com a flag manual `--incluir-paginas`.
