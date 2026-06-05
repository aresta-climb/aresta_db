# Especificação: Quality Guard (CI/CD)

## 1. Visão Geral
Este sistema automatiza a revisão técnica de croquis submetidos ao repositório central. Ele utiliza scripts Python rodando em GitHub Actions para auditar a qualidade dos dados e fornecer feedback imediato aos colaboradores.

## 2. Requisitos de Validação

### 2.1. Nível Crítico (Bloqueia o Merge)
São requisitos fundamentais para o funcionamento do aplicativo mobile. Exemplos:
 * **Croqui válido:** O croqui deve ser compilado e estar íntegro.
 * **Geolocalização:** Presença de coordenadas válidas (Lat/Long).
 * **Referências de Imagem:** Todas as imagens citadas nos arquivos .md devem existir fisicamente na pasta /imagens.

### 2.2. Nível Informativo (Sugestões de Qualidade)
Melhoram a experiência do usuário, mas não impedem o funcionamento. Isso adiciona uma camada de gamificação que ajudará a melhorar a qualidade dos croquis ao longo do tempo. Exemplos:
 * **Links Externos:** Verificação de links para Google Maps ou Wikiloc.
 * **Memória Histórica:** Percentual de preenchimento do campo conquistador.
 * **Densidade de Informação:** Verificação de descrições mínimas de acesso ao setor.

## 3. Fluxo de Trabalho da Action
 1. **Trigger:** A Action é disparada em qualquer pull_request que altere arquivos na pasta database/ (serão criados pela ferramenat de edição).
 2. **Auditoria:** O script health_check.py varre os arquivos modificados, verificando se a formatação está correta e se os requisitos críticos e informativos estão sendo atendidos. 
 3. **Relatório:** Um comentário formatado em Markdown é postado na PR com o sumário dos erros e acertos.
 4. **Status Check:** Se houver erro crítico, o Job falha (exit 1), sinalizando ao GitHub que a PR não está pronta para merge.

## 4. Configuração do Repositório (Proteção de Branch)
Para garantir a eficácia do sistema, a branch main deve ser configurada com:
 * **Require status checks to pass before merging:** Selecionar o job de auditoria.
 * **Require branches to be up to date before merging:** Garante que o teste foi feito com a versão mais recente da base.

Essa estrutura transforma o repositório em uma base de dados "viva" e confiável, onde a tecnologia ajuda a manter o padrão que a comunidade de escalada espera.