# Spec Delta

## ADDED Requirements

### Requirement: Isolamento Global Automático de Cofre de Credenciais e Diretório de Dados na Suíte de Testes
A infraestrutura global de testes (`conftest.py`) e a biblioteca `editor/core/gerenciador_sessao_fake.py` SHALL garantir que nenhuma execução do `pytest` acesse ou modifique o cofre de credenciais real do sistema operacional (`WinVaultKeyring`, `macOS.Keyring`, `SecretService`, `KWallet`) nem o diretório de dados real do usuário (`%APPDATA%/Editor Aresta` ou equivalente).

#### Scenario: Backend de Keyring determinístico em memória ativo por padrão em todos os testes
- **WHEN** qualquer teste da suíte é executado pelo `pytest`
- **THEN** uma fixture `autouse=True` no `conftest.py` SHALL instalar uma instância limpa de `CofreChaveiroFake` (backend de `keyring` 100% em memória) e redirecionar `ARESTA_DIRETORIO_DADOS` para um diretório temporário isolado
- **AND** chamadas diretas ou indiretas a `GerenciadorSessao()`, `keyring.get_password()`, `keyring.set_password()` ou `keyring.delete_password()` SHALL operar exclusivamente sobre o `CofreChaveiroFake` em memória e sobre o diretório temporário do teste, preservando intacta qualquer sessão real do desenvolvedor

#### Scenario: Simulação determinística de falhas de cofre via `CofreChaveiroFake`
- **WHEN** um teste configura `CofreChaveiroFake` para simular erro de leitura, escrita ou remoção de senha
- **THEN** o backend em memória SHALL lançar a exceção configurada de forma determinística sem necessidade de `unittest.mock.patch` sobre funções globais do módulo `keyring`
