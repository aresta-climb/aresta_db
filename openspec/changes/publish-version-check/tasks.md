## 1. Testes de Integração e TDD Inicial (Princípios III, IV e V)

- [ ] 1.1 Criar testes de integração do fluxo de publicação definindo cenários de bloqueio por desatualização, sucesso e falha de rede.
- [ ] 1.2 Criar arquivos de testes unitários (`_test.py`) para o Worker e Utilitários antes de sua implementação (TDD). 
- [ ] 1.3 Assegurar 100% de cobertura de código (`unit test coverage`) cobrindo 100% dos fluxos e comportamentos da funcionalidade.

## 2. Implementação do Worker de Checagem (QThread)

- [ ] 2.1 Implementar a classe assíncrona `TarefaChecarVersao` (herdando de `QThread`) em `editor/core/worker.py` capaz de bater na rota `GET /repos/aresta-climb/aresta_db/releases/latest`, passando nos testes falhos.
- [ ] 2.2 Configurar a injeção do header de Authorization com o Token retornado de `auth.recuperar_token()`, mitigando limits.
- [ ] 2.3 Programar a comparação básica de SemVer pegando a key `tag_name` do retorno JSON da API contra a constante local presente no módulo `version`.
- [ ] 2.4 Determinar e instanciar os 3 sinais fundamentais da thread: `versao_ok`, `desatualizado(str_nova_versao)` e `erro_rede`.

## 3. Bloqueio no PublishController

- [ ] 3.1 Modificar o método `iniciar_publicacao` da classe `PublishController` instanciando primeiro uma `QProgressDialog` com aviso de "Verificando versão..." conectada ao worker recém criado.
- [ ] 3.2 Conectar os callbacks. Somente o acionamento do callback `_on_versao_ok` invocará o miolo original da função, que continua com o build local e validações.
- [ ] 3.3 Em caso de `erro_rede`, notificar na UI a falha mas conceder bypass (fallback aberto).

## 4. Hard Restart (Fechando o ciclo)

- [ ] 4.1 Implementar uma função limpa (ex: `reiniciar_aplicativo()` via Utils/Core) que executa `subprocess.Popen([sys.executable])` e comanda `QApplication.quit()` imediatamente, guiada por testes (mocking `subprocess`).
- [ ] 4.2 No callback `_on_desatualizado` instanciar uma janela Custom QMessageBox de Erro/Aviso.
- [ ] 4.3 Popular esse aviso detalhando a obrigatoriedade da reinicialização devido a disparidade estrutural, oferecendo o botão "Reiniciar Editor".
