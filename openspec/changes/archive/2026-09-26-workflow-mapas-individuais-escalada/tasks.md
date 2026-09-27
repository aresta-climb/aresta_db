# Tarefas de Implementação: Workflows de Agente para Mapas Individuais de Escalada

## 1. Compressão Determinística por Entidade (`preparar_submissao_lib.py`)

- [x] 1.1 Criar testes em `scripts/preparar_submissao_lib_test.py` verificando que imagens migradas de `raw_pdf_contents/` vinculadas a `escaladas[].mapas` são redimensionadas para 1.0 MP com WebP Q85, enquanto imagens vinculadas a `Setor.mapas` são redimensionadas para 2.5 MP com WebP Q85.
- [x] 1.2 Atualizar a rotina de migração de imagens em `scripts/preparar_submissao_lib.py` para usar `comprimir_imagem_para_bytes_webp` com o perfil correto conforme o contexto de vínculo (escalada vs. setor/grupo) e verificar aprovação dos testes.

## 2. Pipeline de Extração e OCR de Mapas (`scripts/`)

- [x] 2.1 Criar testes em `scripts/preparar_extracao_de_mapas_test.py` (ou suite correspondente) validando que `preparar_extracao_de_mapas.py` indexa mapas dentro de `escaladas[].mapas`, gerando o arquivo JSON em `raw_mapas/` com metadados da escalada e disparando o OCR.
- [x] 2.2 Atualizar `scripts/preparar_extracao_de_mapas.py` para percorrer recursivamente mapas de escaladas e gerar metadados com `"pertence_a_escalada": true`, `"escalada_nome"` e `"escalada_indice"`.
- [x] 2.3 Criar testes em `scripts/finalizar_mapas_test.py` (ou suite correspondente) validando que `finalizar_mapas.py` injeta dimensões e pontos de interesse identificados de volta para `escaladas[].mapas` no arquivo Markdown de origem.
- [x] 2.4 Atualizar `scripts/finalizar_mapas.py` para sincronizar os dados processados em `raw_mapas/` de volta na escalada alvo no Markdown.

## 3. Instruções e Heurísticas das Skills de Agentes (`.agents/skills/`)

- [x] 3.1 Atualizar `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md` com heurísticas explícitas para o subagente `ConversorMarkdown` identificar imagens dedicadas a escaladas específicas (close-ups de boulder, saída/sit-start, croqui vertical de via) vs. mapas gerais do setor, ensinando a sintaxe YAML de `escaladas[].mapas` e removendo instruções legadas de `caminho_imagem_croqui`.
- [x] 3.2 Atualizar `.agents/skills/mapa_extrair_pontos_de_interesse/SKILL.md` instruindo o subagente `ExtratorMapas` a reconhecer pontos de interesse semânticos típicos de mapas de escalada (início, saída, proteções, crux).
- [x] 3.3 Atualizar `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md` reforçando que blocos com fotos gerais e fotos de detalhe de escaladas permanecem no mesmo arquivo de setor/bloco.

## 4. Integração e Validação do Pipeline Completo

- [x] 4.1 Executar a suíte de testes de scripts e compilação do `aresta_db` (`pytest scripts/`) verificando 100% de sucesso.
- [x] 4.2 Simular a conversão e compilação de uma parte de croqui contendo mapa geral e mapa de escalada, verificando que o arquivo gerado atende ao schema Protobuf e passa na validação sem warnings.
