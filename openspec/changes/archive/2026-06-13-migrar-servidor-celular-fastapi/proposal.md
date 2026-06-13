## Why

O atual `ServidorCelular` utiliza o módulo embutido `http.server` do Python. A sua implementação atual recalcula o ETag computando o hash SHA-256 de cada arquivo do sistema a cada requisição GET. Isso cria um enorme gargalo de performance de CPU e I/O de disco, especialmente ao carregar recursos pesados ou múltiplos arquivos. Migrar o servidor HTTP para uma stack moderna e assíncrona (como FastAPI e Uvicorn) resolverá esses gargalos nativamente usando metadados dos arquivos (`os.stat`) para ETags, além de trazer suporte completo a requisições do tipo Range, Keep-Alive, e garantir um desligamento (shutdown) do servidor muito mais limpo.

## What Changes

- Substituir a implementação do `ThreadedHTTPServer` e `ManipuladorHandshake` (baseada em `http.server`) por uma aplicação FastAPI ou Starlette rodando sobre `uvicorn`.
- O endpoint de `/handshake` passará a ser uma rota na nova aplicação, emitindo de forma thread-safe o sinal `dispositivo_conectado` do PyQt.
- Remoção da lógica pesada de cálculo de hash `_calcular_sha256`; delegação do controle de ETag e cache (código HTTP 304) nativamente para o módulo `StaticFiles`.
- A lógica de `shutdown` do servidor passará a utilizar as flags nativas do uvicorn (ex: `server.should_exit = True`), dispensando os atuais hacks de contorno de travamento de threads da UI.

## Capabilities

### New Capabilities
*(Nenhuma funcionalidade de domínio nova introduzida, trata-se de um refatoramento infraestrutural de um serviço já existente).*

### Modified Capabilities
*(Os requisitos essenciais de comportamento do usuário continuam os mesmos).*

## Impact

- **Código:** Modificação estrutural do arquivo `editor/core/servidor_celular.py`, buscando manter a simplicidade arquitetural (Princípio 5).
- **Dependências:** Inclusão de `uvicorn` e `fastapi`.
- **Testes (TDD):** Implementação baseada em TDD (Princípio 3), criando testes de integração (Princípio 4) antes de refatorar o `ServidorCelular`.
- **Empacotamento (PyInstaller):** A integração ASGI exigirá declaração explícita de imports ocultos (hidden imports) para o `uvicorn` e `fastapi` no script de build do PyInstaller para garantir que os arquivos e hooks da biblioteca sejam copiados no binário final.
- **Integração PyQt:** O loop assíncrono do uvicorn (ASGI) rodará em uma thread dedicada em background, o que requer cuidado na emissão correta de sinais para a thread principal da UI (Qt).
