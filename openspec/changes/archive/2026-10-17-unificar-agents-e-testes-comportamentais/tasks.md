# Tasks

## 1. Padronização de Governança no `aresta_db`

- [x] 1.1 Atualizar `c:\Renato\Devel\aresta-climb\aresta_db\AGENTS.md` com os 8 princípios canônicos (I a VII universais + VIII de Edições de Estado via `QUndoCommand` na pilha `historico`), corrigindo a menção indevida ao Fixalog e verificando a presença das 8 seções numeradas
- [x] 1.2 Remover a skill redundante `c:\Renato\Devel\aresta-climb\aresta_db\.agents\skills\principios_desenvolvimento` e verificar que o diretório não existe mais
- [x] 1.3 Atualizar `c:\Renato\Devel\aresta-climb\aresta_db\openspec\config.yaml`, `c:\Renato\Devel\aresta-climb\aresta_db\GUIA_DO_DESENVOLVEDOR.md` e corrigir o cabeçalho estrutural de `c:\Renato\Devel\aresta-climb\aresta_db\openspec\specs\principios-implementacao\spec.md` (`## Requirements`), verificando com busca textual que não restam links quebrados para `PRINCIPIOS.md` e que `openspec validate "unificar-agents-e-testes-comportamentais"` executa sem avisos

## 2. Padronização de Governança no `aresta_api`

- [x] 2.1 Criar `c:\Renato\Devel\aresta-climb\aresta_db\aresta_api\AGENTS.md` (e sincronizar em `aresta_app\frontend\lib\aresta_api\AGENTS.md` se aplicável) com os princípios I a VII universais e o Princípio VIII de Design e Evolução de Schemas Protobuf (`Enum` encapsulado com `INDEFINIDO = 0`, `oneof` encapsulado com `ONEOF_CONTEUDO`, no máximo um `conteudo_markdown` por mensagem), verificando a criação do arquivo
- [x] 2.2 Atualizar `c:\Renato\Devel\aresta-climb\aresta_db\aresta_api\beta_proto_test.py` e `c:\Renato\Devel\aresta-climb\aresta_db\aresta_api\README.md` para referenciar `AGENTS.md` e executar `uv run pytest aresta_api/beta_proto_test.py aresta_api/proto_validacao_test.py` verificando que os testes passam

## 3. Padronização de Governança no `aresta_app`

- [x] 3.1 Atualizar `c:\Renato\Devel\aresta-climb\aresta_app\AGENTS.md` com os princípios I a VII universais (adaptados para `.dart` / `_test.dart`) e o Princípio VIII de Testes de Widget, Isolates Reais e Arquitetura Reativa, verificando a estrutura completa do arquivo
- [x] 3.2 Atualizar `c:\Renato\Devel\aresta-climb\aresta_app\openspec\config.yaml`, `CONTRIBUTING.md`, `frontend\README.md` e `frontend\lib\utils\README.md` substituindo referências a `PRINCIPIOS.md` por `AGENTS.md`, e verificar com busca textual que não restam ocorrências de `PRINCIPIOS.md` fora de arquivos históricos

## 4. Padronização de Governança no `aresta_backend`

- [x] 4.1 Renomear `c:\Renato\Devel\aresta-climb\aresta_backend\AGENT.md` para `AGENTS.md` e atualizar seu conteúdo com os princípios I a VII universais (para TypeScript/Deno/Cloudflare Workers com `_test.ts`) e o Princípio VIII de Eficiência de Borda (Edge-First) e Isolamento em `compartilhado/`, verificando que `AGENT.md` foi removido e `AGENTS.md` está presente
- [x] 4.2 Atualizar `c:\Renato\Devel\aresta-climb\aresta_backend\README.md` para referenciar `AGENTS.md` na seção de qualidade e testes, verificando a integridade do link

## 5. Padronização de Governança no `arestaclimb.com`

- [x] 5.1 Atualizar `c:\Renato\Devel\aresta-climb\arestaclimb.com\AGENTS.md` com os princípios I a VII universais (para JavaScript/Vite/Vitest com `.test.js`) e o Princípio VIII de Eficiência Client-Side First e Arquitetura Web Leve, verificando a presença das 8 seções
- [x] 5.2 Atualizar `c:\Renato\Devel\aresta-climb\arestaclimb.com\openspec\config.yaml` e `README.md` para referenciar explicitamente `AGENTS.md`, verificando o conteúdo atualizado

## 6. Padronização de Governança no `fixalog`

- [x] 6.1 Renomear `c:\Renato\Devel\aresta-climb\fixalog\PRINCIPIOS.md` para `AGENTS.md`, remover `c:\Renato\Devel\aresta-climb\fixalog\.agents\agents.md`, e atualizar `AGENTS.md` com os princípios I a VII universais (corrigindo a referência de `.py` para `.dart` / `_test.dart` e a numeração duplicada) e o Princípio VIII de Operação Offline-First e Integridade Pericial Criptográfica
- [x] 6.2 Atualizar `c:\Renato\Devel\aresta-climb\fixalog\README.md`, `openspec\config.yaml`, `openspec\README.md`, `docs\ROTEIRO_INTEGRACAO_ARESTA.md` e `app\test\architecture\test_structure_mirror_test.dart` substituindo `PRINCIPIOS.md` por `AGENTS.md`, e executar `flutter test test/architecture/test_structure_mirror_test.dart` em `fixalog/app` para verificar que o teste arquitetural de espelhamento 1:1 passa
