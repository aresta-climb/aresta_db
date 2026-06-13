## Context

O atual servidor HTTP local usado no editor (`editor/core/servidor_celular.py`) é construído com `http.server` (biblioteca padrão do Python). Este servidor roda em uma thread dedicada e possui problemas significativos de performance e gerenciamento:
1. Para contornar a falta de suporte nativo a ETags/If-None-Match, a implementação atual lê todo o arquivo do disco em pedaços e calcula o hash SHA-256 a cada requisição GET, consumindo alta CPU e bloqueando o I/O se o croqui for pesado.
2. A interrupção limpa do `http.server` bloqueante na interface gráfica do PyQt exige uma arquitetura complexa de "shutdown rodando em outra thread" para evitar travamentos da UI, sujeita a condições de corrida e deadlocks.

## Goals / Non-Goals

**Goals:**
- Prover tempos de resposta ultra rápidos para os assets, delegando o controle de ETag e "Modified-Since" para o file system (`os.stat`).
- Implementar um mecanismo de desligamento seguro do servidor.
- Preservar a integração thread-safe com os sinais do PyQt.

**Non-Goals:**
- Alterar a interface com o usuário ou o comportamento de visualização e escaneamento do QR Code.
- Implementar funcionalidades além de hospedagem estática e um endpoint de heartbeat/handshake.

## Decisions

- **FastAPI/Starlette com Uvicorn:** Vamos usar `FastAPI` instanciado programaticamente em conjunto com `uvicorn.Server`. Para arquivos estáticos, o módulo `StaticFiles` da Starlette cuidará perfeitamente das complexidades de ETags e cache de navegadores baseados em metadados do arquivo em vez de hash integral.
- **Thread Dedicada com Event Loop:** O loop asyncio do uvicorn não pode bloquear o loop do Qt. Manteremos a inicialização em uma thread separada em background. Quando instanciarmos o uvicorn nesta nova thread, ele criará seu próprio loop assíncrono interno.
- **Emissão Thread-Safe:** O endpoint `/handshake` emitirá o sinal `dispositivo_conectado.emit()`. Graças aos Queued Connections automáticos do Qt, invocar isso em threads separadas (no uvicorn) em direção à UI thread é totalmente seguro.
- **Desligamento Seguro:** Para interromper o servidor, setaremos flag nativa do uvicorn `self.server.should_exit = True`, evitando as lambanças de threads do `shutdown()` atual.

## Risks / Trade-offs

- **Dependências Externas** → Substituir parte da biblioteca padrão (`http.server`) por pacotes externos (`uvicorn`, `fastapi`). Trade-off aceitável dado o abismo de performance e confiabilidade, além de já estarmos possivelmente usando ambientes com vários outros pacotes instalados.
- **Integração PyInstaller** → Frameworks ASGI como Uvicorn e FastAPI frequentemente utilizam carregamento dinâmico que o PyInstaller não detecta automaticamente. Será necessário atualizar o arquivo `.spec` (ex: `hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'fastapi']`) e incluir metadados.
- **TDD e Testes (Princípios 3 e 4)** → Vamos escrever testes de integração validando o contrato HTTP entre o servidor e um cliente mock antes de modificar a classe real (Red-Green-Refactor). O servidor será testado em isolamento.
