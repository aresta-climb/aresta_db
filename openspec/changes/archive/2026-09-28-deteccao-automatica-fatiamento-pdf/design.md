# Design Técnico: Detecção Automática de Fatiamento de Imagens em PDFs

## Context

O script `scripts/repartir_pdf.py` recebe um arquivo `croqui_original.pdf` e o divide em sub-PDFs e imagens extraídas com base no `partes.json`.
PDFs gerados por ferramentas modernas de editoração (Canva, InDesign, Illustrator) aplicam achatamento de transparências (*transparency flattening*), particionando fotos com sobreposições vetoriais em grades de fatias adjacentes.
Anteriormente, o sistema dependia de intervenção humana ou instruções explícitas para passar a flag `--incluir-paginas`, gerando também dezenas de recortes quebrados `pX_iY.webp` que confundiam os agentes de conversão para Markdown.

## Goals / Non-Goals

**Goals:**
- Implementar algoritmo geométrico determinístico em `scripts/repartir_pdf.py` para detectar páginas com imagens fatiadas em mosaico.
- Ativar automaticamente a renderização de páginas completas (`pX.webp`) para páginas fatiadas, sem necessidade de `--incluir-paginas`.
- Suprimir a extração de recortes individuais fragmentados (`pX_iY.webp`) em páginas onde o fatiamento foi detectado e a página completa foi renderizada, mantendo a pasta limpa.
- Simplificar as instruções de workflows e skills, eliminando exigências manuais desnecessárias.
- Assegurar 100% de cobertura de testes unitários em `scripts/repartir_pdf_test.py`.

**Non-Goals:**
- Remover a flag `--incluir-paginas`: ela continuará existindo para forçar manualmente a extração de páginas completas se o usuário desejar.
- Modificar ferramentas externas de OCR ou compilação de croquis.

## Decisions

### Decisão 1: Detecção baseada em adjacência de bordas (tiling) e área combinada
- **Abordagem**: Duas imagens são consideradas fatias adjacentes se compartilham borda horizontal (`abs(r1.x1 - r2.x0) <= tol` ou vice-versa, com sobreposição no eixo Y) ou borda vertical (`abs(r1.y1 - r2.y0) <= tol` ou vice-versa, com sobreposição no eixo X). Uma página é considerada fatiada se contiver pares adjacentes de fatias e sua união cobrir uma área expressiva da página (ou contiver múltiplos fragmentos em malha).
- **Alternativa rejeitada**: Contar apenas o número de imagens por página. Rejeitada porque páginas com logotipos de patrocinadores ou pequenos ícones poderiam gerar falsos positivos.

### Decisão 2: Ativação por página na extração
- **Abordagem**: A avaliação é executada por página dentro de `extrair_imagens_da_parte`. Se uma página individual for detectada como fatiada (ou se `include_pages` global estiver ativo), ela renderiza `pX.webp`.
- **Alternativa rejeitada**: Avaliar apenas o PDF globalmente. A avaliação por página permite tratar documentos híbridos (onde apenas algumas páginas contêm topos fatiados e outras contêm fotos normais isoladas).

### Decisão 3: Supressão de fatias quebradas para páginas fatiadas
- **Abordagem**: Quando uma página é detectada como fatiada e sua versão completa `pX.webp` é renderizada, o script suprime a extração dos recortes individuais fragmentados (`pX_i0`, `pX_i1`, etc.).
- **Motivo**: Nenhum agente ou usuário precisa de fragmentos de parede cortados ao meio. Disponibilizar apenas `pX.webp` elimina ambiguidades para o agente de Markdown.

## Risks / Trade-offs

- **[Risco] Falsos positivos gerando `pX.webp` em páginas normais**:
  - *Mitigação*: A heurística exige adjacência de bordas de dimensões compatíveis e filtro de tamanho mínimo (ignorando ícones minúsculos). Além disso, gerar `pX.webp` em alta resolução não causa perda de dados (é a imagem fiel da página).
- **[Risco] Quebra de testes existentes**:
  - *Mitigação*: Testes existentes em `scripts/repartir_pdf_test.py` utilizam mocks controlados de retângulos. Atualizaremos e expandiremos a suíte de testes com TDD, garantindo 100% de cobertura.
