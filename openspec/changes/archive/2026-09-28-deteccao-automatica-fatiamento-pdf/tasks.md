# Tarefas de Implementação: Detecção Automática de Fatiamento de Imagens

## 1. Testes Unitários de Detecção (TDD)

- [x] 1.1 Escrever testes unitários para as funções geométricas `sao_fatias_adjacentes` e `detectar_fatiamento_pagina` em `scripts/repartir_pdf_test.py` cobrindo casos de fatias adjacentes horizontais, verticais, fotos isoladas e ícones minúsculos, verificando que falham antes da implementação (Red).
- [x] 1.2 Escrever testes unitários em `scripts/repartir_pdf_test.py` cobrindo a ativação automática de `pX.webp` e a supressão de fatias quebradas quando fatiamento for detectado na chamada de `extrair_imagens_da_parte`.

## 2. Implementação da Detecção e Extração Automática

- [x] 2.1 Implementar as funções `sao_fatias_adjacentes` e `detectar_fatiamento_pagina` em `scripts/repartir_pdf.py`, verificando aprovação dos testes específicos de geometria (Green).
- [x] 2.2 Integrar a detecção automática dentro de `extrair_imagens_da_parte` em `scripts/repartir_pdf.py`, renderizando a página completa `pX.webp` e suprimindo fatias fragmentadas para as páginas fatiadas, com log informativo no console.
- [x] 2.3 Executar a suíte de testes com `pytest scripts/repartir_pdf_test.py --cov=scripts.repartir_pdf --cov-report=term-missing` e verificar 100% de cobertura de código.

## 3. Simplificação de Workflows e Skills

- [x] 3.1 Atualizar `.agents/workflows/processar_croqui_completo.md` na Fase 1 (Passos 5 e 6) para remover a menção obrigatória à flag `--incluir-paginas`, documentando que o particionador detecta automaticamente páginas com mosaicos.
- [x] 3.2 Atualizar `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md` simplificando a invocação do comando `repartir_pdf.py` e explicando o mecanismo de auto-detecção de fatiamento.
- [x] 3.3 Atualizar `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md` para instruir o uso natural de `pX.webp` gerado automaticamente quando o documento contiver páginas fatiadas.

## 4. Validação Integrada

- [x] 4.1 Executar teste ponta a ponta no PDF de `database/br_mg_santa_luzia_morro_do_carrapato_setor_covide` sem a flag `--incluir-paginas`, confirmando que as páginas fatiadas continuam sendo extraídas como `pX.webp` de alta resolução.
- [x] 4.2 Validar a especificação completa executando `openspec validate deteccao-automatica-fatiamento-pdf --strict`.
