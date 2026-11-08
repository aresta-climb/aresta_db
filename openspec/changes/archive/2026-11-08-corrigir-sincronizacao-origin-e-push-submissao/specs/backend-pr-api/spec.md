## MODIFIED Requirements

### Requirement: Validação de Escopo de Pastas Restritas
O serviço `create-pr` MUST inspecionar a lista de arquivos modificados na branch da sugestão antes de formalizar a Pull Request, distinguindo claramente quando a branch não existe no repositório remoto.

#### Scenario: Alterações Exclusivas em database/
- **WHEN** todos os arquivos alterados na branch `edicao-*` ou `sugestao-*` pertencerem exclusivamente ao caminho `database/`
- **THEN** o serviço MUST prosseguir para a criação do Pull Request

#### Scenario: Tentativa de Modificação Fora de database/
- **WHEN** a branch contiver alterações em arquivos fora de `database/` (ex: workflows, código-fonte ou raiz)
- **THEN** o serviço MUST deletar a branch remota no GitHub e responder com HTTP 400 Bad Request descrevendo a violação de segurança

#### Scenario: Branch Não Encontrada no Repositório do GitHub (HTTP 404)
- **WHEN** a inspeção de commits da branch no GitHub (`compareCommits`) falhar com status 404 (`Not Found`)
- **THEN** o serviço `create-pr` MUST responder com HTTP 400 Bad Request contendo mensagem explícita informando que a branch da proposta não foi encontrada no GitHub porque o envio dos commits (`git push`) não foi efetivado
