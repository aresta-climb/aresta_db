# Proposta: Onda 3 - Tipagem Estática da Lógica de Aplicação, Comandos e Controladores

## Por que (Motivação)

No Editor Aresta, as mutações de dados no modelo Protobuf e a orquestração dos fluxos de edição (salvamento, compilação, publicação e manipulação de mapas) são conduzidas por comandos de Undo/Redo (\QUndoCommand\) e controladores de aplicação (\QObject\).

Por serem altamente dinâmicos e manipularem estruturas complexas de mensagens Protobuf geradas, estes módulos eram historicamente vulneráveis a:
1. Erros de mutação com tipos incompatíveis ao deserializar comandos do diário de recuperação.
2. Incompatibilidade entre tipos de argumentos passados pelos controladores e consumidos pelos workers de background.
3. Tratamento de \None\ em nós de POIs, coordenadas e coleções repetidas.
4. Conexões de sinais Qt sem validação estrita de assinaturas.

A **Onda 3** moderniza e blinda toda a camada de comandos e controladores com **Tipagem Estática Estrita (\strict = true\)**, garantindo que as mutações no modelo Protobuf e os controladores operem sob contratos de tipo rígidos e verificáveis.

---

## O que será feito (Escopo)

1. **Comandos de Histórico e Mutações (\ditor/commands/\)**:
   - Tipagem completa de \ditor/commands/comandos_protobuf.py\ (classes de comando para campos primitivos, coleções repetidas, \oneof\, serialização/deserialização e nós auxiliares).
   - Tipagem de \ditor/commands/comandos_mapas.py\ (criação, edição, exclusão e arraste de pontos de interesse).

2. **Controladores de Aplicação (\ditor/controllers/\)**:
   - Tipagem de \ditor/controllers/croqui_controller.py\ (gerenciamento do ciclo de vida do croqui, estado dirty e sinais).
   - Tipagem de \ditor/controllers/mapas_controller.py\ (coordenação de mapas, POIs e transições).
   - Tipagem de \ditor/controllers/compilacao_controller.py\ (orquestração de compilação assíncrona).
   - Tipagem de \ditor/controllers/publish_controller.py\ (publicação, PRs, branch lifecycle e integração Git Proxy).

3. **Utilitários e Build de Pacote**:
   - Tipagem de \ditor/build.py\.

4. **Expansão do Teste Guardião**:
   - Atualização de \	ests/tipagem_estatica_test.py\ para incluir todos os módulos de \ditor/commands/\ e \ditor/controllers/\ nas suítes automatizadas de validação MyPy e AST.
