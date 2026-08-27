# backend-notificacoes-revisao Specification

## Purpose
Define a infraestrutura de backend e automação acionada por eventos do GitHub para identificar os mantenedores responsáveis por um croqui modificado e disparar notificações proativas via E-mail (Resend) e WhatsApp.

## Requirements

### Requirement: Tabela de Mantenedores e Preferências de Notificação
O banco de dados PostgreSQL do Supabase MUST manter o registro dos mantenedores de croquis com seus canais de contato e padrões de croquis sob sua responsabilidade.

#### Scenario: Estrutura da tabela de mantenedores
- **WHEN** a tabela `mantenedores_croquis` for consultada
- **THEN** ela MUST conter os campos `id`, `usuario_id`, `nome`, `email`, `whatsapp` e a lista `padrao_croquis`

### Requirement: Disparo de Notificações via GitHub Action e Edge Function
O sistema MUST identificar os mantenedores responsáveis quando uma Pull Request de sugestão de croqui for aberta ou receber novos comentários e enviar alertas formatados.

#### Scenario: Abertura de nova Pull Request
- **WHEN** uma Pull Request com prefixo `sugestao-` for aberta no repositório `aresta_db`
- **THEN** o workflow do GitHub Actions MUST identificar os arquivos modificados dentro de `database/<croqui>/`
- **THEN** a Edge Function `notificar-revisao` MUST ser acionada enviando o nome do croqui, autor, link do PR e descrição
- **THEN** o sistema MUST enviar um e-mail formatado via Resend para todos os mantenedores responsáveis pelo croqui
- **THEN** se o mantenedor possuir número de WhatsApp cadastrado, o sistema MUST enviar uma mensagem via Gateway com o resumo da solicitação

#### Scenario: Degradação graciosa em falhas de notificação
- **WHEN** ocorrer indisponibilidade temporária no Gateway de WhatsApp ou serviço de e-mail
- **THEN** a falha MUST ser registrada nos logs do backend sem interromper o fluxo da Pull Request no GitHub
