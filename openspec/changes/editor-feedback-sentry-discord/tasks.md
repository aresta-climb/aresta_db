## 1. Coleta de Diagnóstico e Metadados do Sistema

- [ ] 1.1 Criar testes unitários para coleta de dados de diagnóstico do sistema (`editor/core/coletor_relato_test.py`)
- [ ] 1.2 Implementar biblioteca de diagnóstico e empacotamento de relatos (`editor/core/coletor_relato.py`)

## 2. Cliente de Webhook do Discord com Suporte Multipart

- [ ] 2.1 Criar testes unitários para o despachante de Webhook do Discord com mock de requisições HTTP multipart (`editor/core/cliente_webhook_discord_test.py`)
- [ ] 2.2 Implementar biblioteca de envio ao Discord com cartões visuais formatados, cores por categoria e imagem anexada (`editor/core/cliente_webhook_discord.py`)

## 3. Extensão da Telemetria Sentry para Envio de Relatos

- [ ] 3.1 Criar testes unitários para a função de envio de relato no Sentry com anexos binários e retorno de `event_id` (`editor/core/telemetria_test.py`)
- [ ] 3.2 Implementar função `enviar_relato_sentry` e geração de URL de rastreabilidade em `editor/core/telemetria.py`

## 4. Componente Gráfico de Quadro de Anotação e Tarjas de Privacidade

- [ ] 4.1 Criar testes unitários para o quadro de anotação, ferramentas de desenho, tarja preta e desfazer (`editor/views/widget_quadro_anotacao_test.py`)
- [ ] 4.2 Implementar componente `WidgetQuadroAnotacao` com ferramentas de caneta, retângulo, tarja opaca e exportação de imagem (`editor/views/widget_quadro_anotacao.py`)

## 5. Diálogo Modal de Relato e Tarefa Assíncrona de Envio

- [ ] 5.1 Adicionar ícones de relato, anotação e tarja em `editor/views/estilo.py` e atualizar `editor/views/estilo_test.py`
- [ ] 5.2 Criar testes unitários para o diálogo modal de relato e a tarefa assíncrona de envio (`editor/views/dialogos/dialogo_relato_usuario_test.py`)
- [ ] 5.3 Implementar diálogo `DialogoRelatoUsuario` com categorização, prévia anotada e confirmação visual de envio (`editor/views/dialogos/dialogo_relato_usuario.py`)

## 6. Integração nos Pontos de Entrada da Interface Gráfica

- [ ] 6.1 Adicionar ação de relato e atalhos `F12` / `Ctrl+Shift+F` na barra superior da Janela Principal (`editor/legacy_views/area_principal.py`) e atualizar testes
- [ ] 6.2 Adicionar botão de envio de relato na Tela de Seleção de Croquis (`editor/legacy_views/tela_de_carregamento.py`) e atualizar testes
- [ ] 6.3 Adicionar botão de reporte na Tela de Abertura/Login (`editor/views/tela_de_abertura.py`) e atualizar testes

## 7. Testes de Integração de Ponta a Ponta e Validação

- [ ] 7.1 Criar teste de integração ponta a ponta simulando captura de tela, anotação, despacho conjunto Sentry/Discord e ligação direta (`editor/views/dialogos/dialogo_relato_usuario_integracao_test.py`)
- [ ] 7.2 Executar suite completa de testes com pytest e verificar 100% de cobertura de código
