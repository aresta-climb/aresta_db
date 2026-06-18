## 1. Criação do Workflow Principal

- [x] 1.1 Criar o arquivo `.agents/workflows/processar_croqui_completo.md`
- [x] 1.2 Definir o frontmatter e a descrição base do workflow detalhando as fases

## 2. Configuração de Sub-agentes

- [x] 2.1 Adicionar a declaração de infraestrutura para criar o tipo de sub-agente `SeparadorPDF` usando a skill `separar_croqui_pdf_em_partes`
- [x] 2.2 Adicionar a declaração para criar o tipo `ConversorMarkdown` associado à skill de conversão md
- [x] 2.3 Adicionar a declaração para criar o tipo `ExtratorMapas` com as regras de extração e correção de pontos

## 3. Máquina de Estado e Execução

- [x] 3.1 Escrever as regras de verificação de estado implícito (presença de `partes.json`, presença de `.md`, `compilado.md`)
- [x] 3.2 Escrever as instruções para execução da Fase 1 (invocar sub-agente, rodar `repartir_pdf.py` e pausar)
- [x] 3.3 Escrever as instruções para execução da Fase 2 (executar `invoke_subagent` com array baseado no `partes.json` e lidar com auto-correção)
- [x] 3.4 Escrever as instruções para a Fase 3 (extração de mapas com retry de auto-correção e compilação final)

## 4. Lógica de Auto-Correção (Auto-heal)

- [x] 4.1 Definir explicitamente o prompt do Orquestrador sobre como analisar respostas de erro dos sub-agentes
- [x] 4.2 Adicionar o limite de tentativas (retry de até 3 vezes por parte que falhou) antes de pedir intervenção humana
