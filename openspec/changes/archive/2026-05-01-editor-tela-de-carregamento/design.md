## Contexto

A "Tela de Carregamento" serve como o hub inicial para gerenciar croquis experimentais. Atualmente, o fluxo de criação de novos croquis é manual e propenso a erros, pois não gera o arquivo de configuração `croqui.yaml` necessário para a compilação.

## Objetivos / Não-Objetivos

**Objetivos:**
- Implementar um diálogo (`DialogoNovoCroqui`) robusto para coleta de metadados.
- Automatizar a geração do ID seguindo o padrão organizacional do projeto.
- Garantir que todo novo croqui comece em um estado "compilável" (com `croqui.yaml` e primeiro build realizado).

**Não-Objetivos:**
- Implementar edição avançada de metadados nesta fase (foco apenas na criação).
- Alterar o esquema de diretórios existente.

## Decisões Técnicas

- **Interface do Diálogo:** Utilizaremos `QFormLayout` para o formulário de metadados no `DialogoNovoCroqui`.
- **Geração Dinâmica de ID:** O campo de ID será atualizado em tempo real via sinais do Qt (`textChanged`) conectando os campos de Nome, Cidade, Estado e País.
- **Normalização de Strings:** Implementaremos uma função utilitária `para_id_croqui(texto)` que remove acentos, converte para minúsculas e aplica camelCase/snake_case conforme necessário para o padrão do ID.
- **Inicialização do YAML:** O arquivo `croqui.yaml` será gerado seguindo rigorosamente a estrutura da mensagem `Croqui` definida em `croqui.proto`. Ele será inicializado com os campos `id`, `nome` e uma lista `picos` contendo um objeto inicial com o `nome` e `estado` coletados. Cidade e País serão utilizados prioritariamente para a composição do ID determinístico.
- **Validação Visual de ID:** Utilizaremos um `QLabel` posicionado ao lado do campo de ID. Este label será atualizado dinamicamente para exibir um ícone (tick verde ou "X" vermelho) e uma mensagem curta. O botão "Criar" será habilitado apenas quando o ID for válido e único.
- **Fluxo de Compilação:** Após a criação dos arquivos, chamaremos a função de compilação (provavelmente via `editor/app/fluxo_carregamento.py`) e exibiremos o progresso no `DialogoProgressoLog`.


## Riscos / Trade-offs

- **Bloqueio de Arquivo (Windows):** A compilação imediata após a criação pode esbarrar em locks de diretório. 
  - **Mitigação:** Garantir que todos os handles de arquivo sejam fechados antes de disparar o compilador.
- **ID Duplicado:** O usuário pode tentar criar um croqui com ID que já existe.
  - **Mitigação:** Adicionar validação no diálogo para verificar a existência da pasta antes de permitir a confirmação.
