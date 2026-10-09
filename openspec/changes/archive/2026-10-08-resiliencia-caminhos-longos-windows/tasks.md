# Tasks

## 1. Sanitização com Limite de 40 Caracteres em Nomes de Arquivos

- [x] 1.1 Escrever testes unitários em `editor/core/imagens_markdown_test.py` cobrindo o truncamento do tronco em 40 caracteres e implementar a lógica em `editor/core/imagens_markdown.py` garantindo que os testes passem com 100% de cobertura
- [x] 1.2 Escrever testes unitários em `editor/views/dialogos/dialogo_inserir_botao_markdown_test.py` cobrindo o truncamento de nomes de anexos em 40 caracteres e implementar em `editor/views/dialogos/dialogo_inserir_botao_markdown.py` garantindo que os testes passem com 100% de cobertura

## 2. Sanitização de Barras Duplas na Telemetria Sentry

- [x] 2.1 Escrever testes unitários em `editor/core/telemetria_test.py` cobrindo a sanitização de caminhos com barras duplas escapadas (`\\`) oriundas de representações `repr()` e tuplas de exceção
- [x] 2.2 Implementar suporte a substituição de barras duplas em `_obter_mapeamento_sanitizacao()` e `sanitizar_texto_caminhos()` em `editor/core/telemetria.py` e verificar aprovação de todos os testes da biblioteca

## 3. Normalização de Caminhos Estendidos em `editor/plataforma` e Deploy

- [x] 3.1 Escrever testes unitários para `normalizar_caminho_estendido` em `editor/plataforma/contrato_test.py`, `editor/plataforma/__init___test.py`, `editor/plataforma/windows/integracao_test.py`, `editor/plataforma/linux/integracao_test.py` e `editor/plataforma/macos/integracao_test.py`
- [x] 3.2 Implementar `normalizar_caminho_estendido` no contrato `AdaptadorPlataforma`, na fachada de `editor/plataforma` e nos adaptadores de cada sistema operacional (prefixando `\\?\` no Windows e resolvendo canonicamente em Linux/macOS)
- [x] 3.3 Consumir `normalizar_caminho_estendido` em `copiar_imagens`, `copiar_anexos` e `force_rmtree` em `scripts/deploy_generated.py`, escrevendo testes em `scripts/deploy_generated_test.py` e garantindo 100% de cobertura

## 4. Otimização Estrutural do Workspace Experimental

- [x] 4.1 Atualizar testes de integração e unitários em `editor/core/workspace_test.py` e `editor/core/croqui_experimental_test.py` para validar a geração dos arquivos compilados diretamente na pasta `compilado/` sem aninhamento redundante de `<croqui_id>`
- [x] 4.2 Ajustar `ExperimentalWorkspace` em `editor/core/workspace.py` e `compilar_croqui` em `editor/core/croqui_experimental.py` para direcionar a compilação e o servidor local para a estrutura compacta, executando a suíte completa de testes do editor com sucesso
