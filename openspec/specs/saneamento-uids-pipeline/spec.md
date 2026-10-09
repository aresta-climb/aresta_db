# saneamento-uids-pipeline Specification

## Purpose

Garante que o pipeline de preparação e validação de dados execute o saneamento automático, contínuo e idempotente de identificadores universais NanoID 14c e a conversão de referências de mapa para novos croquis e rascunhos, assegurando que todas as entidades possuam UIDs válidos antes da auditoria contratual.

## Requirements

### Requirement: Saneamento Idempotente de UIDs em Corrigir Database
O sistema SHALL executar a rotina de saneamento e injeção de UIDs NanoID 14c Base62 durante a execução de `corrigir_database` em `scripts/preparar_submissao_lib.py`, atribuindo UIDs para todas as entidades que não possuírem um UID válido (`Croqui`, `Grupo`, `Setor`, `Escalada`, `PontoDeInteresse` e `Botao`) e convertendo referências de mapas semânticas para `alvo_uid` e `pontos_uids`, preservando integralmente os UIDs pré-existentes.

#### Scenario: Novo Croqui Compilado pela Primeira Vez
- **WHEN** um croqui recém-gerado por agentes ou humanos é processado por `deploy_generated.py` ou `corrigir_database`
- **THEN** o sistema injeta UIDs válidos de 14 caracteres Base62 em todas as entidades e converte as referências de mapa antes da verificação de integridade, sem lançar erros de auditoria

#### Scenario: Preservação de UIDs Existentes Durante Novo Saneamento
- **WHEN** um croqui que já possui entidades com UIDs válidos passa novamente por `corrigir_database`
- **THEN** o sistema mantém os UIDs inalterados para todas as entidades já identificadas e apenas atribui novos UIDs para as entidades recém-adicionadas

### Requirement: Saneamento de Pontos de Interesse na Finalização de Mapas
O script `finalizar_mapas.py` SHALL garantir que todos os pontos de interesse transferidos dos arquivos JSON para os arquivos Markdown possuam UIDs válidos de 14 caracteres Base62 e utilizem o campo `rotulo`, preservando UIDs pré-existentes.

#### Scenario: Transferência de Novos Pontos de Interesse para o Markdown
- **WHEN** o script `finalizar_mapas.py` processa um arquivo JSON de mapa contendo novos pontos de interesse sem UID
- **THEN** o script atribui um NanoID 14c para cada novo ponto e grava no Markdown utilizando a chave `rotulo`
