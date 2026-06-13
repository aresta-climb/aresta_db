## 1. Instalação e Configuração de Dependências

- [x] 1.1 Adicionar bibliotecas `fastapi`, `uvicorn` e `httpx` (para os testes asyncio) no ambiente de desenvolvimento do projeto (via `pip` ou atualizando arquivos de requirements, se existirem).

## 2. Testes de Integração Primeiro (TDD)

- [x] 2.1 Criar arquivo de teste `test_servidor_celular.py` (ou equivalente na pasta de testes).
- [x] 2.2 Escrever teste que simula o boot do servidor e faz requisição `GET /handshake` esperando o JSON de sucesso.
- [x] 2.3 Escrever teste que emula um GET num arquivo estático e depois um GET com `If-None-Match`, aguardando status 304 (Red-Green-Refactor).

## 3. Refatoração de ServidorCelular.py

- [x] 3.1 Excluir as classes baseadas no HTTP clássico do Python: `ManipuladorHandshake` e `ThreadedHTTPServer`.
- [x] 3.2 Substituir a função interna `run_server` do `ServidorCelular.iniciar` por uma implementação ASGI baseada em FastAPI.
- [x] 3.3 Criar a rota GET `/handshake` com `JSONResponse`, garantindo que chame o método `self.dispositivo_conectado.emit()`.
- [x] 3.4 Configurar `StaticFiles(directory=str(self.pasta_compilado))` no FastAPI (para lidar nativamente com ETags e requisições de assets do app móvel).
- [x] 3.5 Instanciar programaticamente `uvicorn.Config` e `uvicorn.Server` passando a porta calculada pelo `obter_porta_disponivel()`.
- [x] 3.6 Iniciar o loop através de `self.server.run()`, armazenando a instância em `self.server` no objeto.
- [x] 3.7 Validar que os testes da etapa 2.2 e 2.3 agora passam (Green).

## 4. Graceful Shutdown

- [x] 4.1 Refatorar o método `ServidorCelular.parar()`. Remover o contorno de usar threads secundárias, passando a enviar apenas o sinal nativo `self.server.should_exit = True` para a instância do uvicorn (se ele estiver rodando).

## 5. Integração PyInstaller e Validação

- [x] 5.1 Atualizar o arquivo `.spec` do PyInstaller adicionando `fastapi` e todo o escopo do `uvicorn` (como `uvicorn.loops`, `uvicorn.protocols`, etc) em `hiddenimports`.
- [x] 5.2 Levantar a interface, Iniciar o Servidor Celular e atestar que QR Code aponta para o lugar correto e que logs de `uvicorn` iniciam bem.
- [x] 5.3 Encerrar o servidor pelo botão "Parar" da interface e validar se a porta foi realmente fechada, se logs constam desligamento e sem travar a UI principal.
