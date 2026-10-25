# undo-redo-protobuf Specification

## Purpose
TBD - created by archiving change add-undo-redo. Update Purpose after archive.
## Requirements
### Requirement: Comandos de Edição Protobuf Genericos
O sistema SHALL encapsular e restringir a criação e execução de comandos granulares (`QUndoCommand`) estritamente à camada de `commands/` coordenados pelos `controllers/` e ferramentas MCP. A interface do usuário (View) na aba de Dados NÃO PODE criar e empilhar comandos diretamente ou mutar propriedades. Todas as alterações de campos singulares (escalares primitivos, renomeações de entidades, submensagens singulares, seleção/limpeza de `oneof` e substituição de item por índice em lista `repeated`) SHALL ser realizadas pelo comando canônico unificado `CmdAlterarCampo` em `editor/commands/comandos_protobuf.py`, guiado por introspecção do `DESCRIPTOR` Protobuf (Reflection).

#### Scenario: Edição Primitiva em Protobuf
- **WHEN** o usuário digita em um campo gerado para um tipo String ou escalar do Protobuf (incluindo o campo `nome` de uma escalada) na View
- **THEN** a View envia a intenção ao Controller apropriado, que cria e empilha um comando `CmdAlterarCampo` (da pasta `commands/`) resolvendo automaticamente o tipo pelo `DESCRIPTOR` e capturando o valor anterior do modelo. Sucessivas digitações ininterruptas no mesmo alvo, campo e `session_id` SHALL invocar o merge (`mergeWith`) do comando para evitar inflar o histórico de desfazer letra por letra.

#### Scenario: Alteração de variante oneof ou submensagem singular via CmdAlterarCampo
- **WHEN** o usuário seleciona outra variante de um `oneof` (ex.: `tipo_escalada` ou `alvo_referencia`), limpa um `oneof` (`valor_novo=None`) ou substitui uma submensagem singular (ex.: `metadados` em `CaminhoNovo`)
- **THEN** `CmdAlterarCampo` detecta via `DESCRIPTOR` se o identificador corresponde a um `oneof` ou `MESSAGE` singular, captura o estado anterior completo (incluindo a variante ativa anterior do `oneof` ou cópia da submensagem) e restaura esse estado exato ao acionar Desfazer (Undo)

#### Scenario: Alteração de item específico de lista repeated por índice via CmdAlterarCampo
- **WHEN** `CmdAlterarCampo` recebe um `campo_nome` indexado no formato `"<campo>.<indice>"` (ex.: `"graduacoes.0"` ou `"conquistadores.1"`)
- **THEN** o comando identifica via `DESCRIPTOR` o campo `repeated`, captura o elemento na posição `<indice>` como `valor_antigo` e substitui apenas aquela posição no `executar_redo()` e no `undo()`

### Requirement: Proteção contra Exclusão Estrutural
O sistema SHALL suportar a reversão de comandos destrutivos que alteram a hierarquia da árvore, gerenciada pela camada MVC, utilizando `CmdRemoverRepeated` para exclusão de itens de listas `repeated` e compondo a limpeza de imagens órfãs em memória através de `CmdMacro` (`CmdRemoverRepeated` + `CmdAlterarImagem`).

#### Scenario: Remoção de item em lista repeated
- **WHEN** o usuário clica no botão "Remover" de uma sub-mensagem gerada dinamicamente na View
- **THEN** a View solicita a exclusão ao Controller correspondente
- **THEN** o Controller instancia `CmdRemoverRepeated` (diretamente ou dentro de um `CmdMacro`) que retém uma cópia profunda (`CopyFrom`) da mensagem excluída
- **WHEN** o usuário aciona Desfazer
- **THEN** o comando reinstrui o Model usando os métodos protegidos (`_adicionar_item_repeated`) a reinserir a mensagem no exato índice de onde foi removida, preservando seu `UID` original e disparando sinais de notificação para a View se atualizar

#### Scenario: Remoção e restauração de imagens em memória associadas a itens excluídos
- **WHEN** o Controller processa a remoção de um item `repeated` que referencia imagens no buffer de memória RAM não mais utilizadas em nenhum outro ponto do croqui
- **THEN** o Controller constrói e empilha um `CmdMacro` combinando `CmdRemoverRepeated` e comandos `CmdAlterarImagem(bytes_novos=None)` para cada imagem órfã
- **WHEN** a operação de remoção for desfeita (Desfazer / Undo)
- **THEN** o `CmdMacro` restaura as imagens no buffer de memória RAM via `CmdAlterarImagem`, reinsere o item na lista via `CmdRemoverRepeated` e emite os sinais de atualização da interface

### Requirement: Guarda de Integridade Estrutural nos Comandos Protobuf
O sistema SHALL validar a pertinência da mensagem alvo à árvore ativa do croqui na instanciação direta de qualquer comando Protobuf canônico originado por ações em tempo de execução (`CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`). Se uma instância de mensagem Protobuf for passada como alvo, não for o nó raiz `Croqui` e não puder ser resolvida na árvore ativa (nem por `UID` no `IndiceUidsModel` nem por caminho estrutural), o comando SHALL lançar imediatamente `ValueError`, impedindo comandos órfãos de entrarem no histórico (`QUndoStack`) ou no diário de persistência. Na deserialização a partir do diário persistido, o comando SHALL aceitar o identificador `alvo` (`caminho_msg`) armazenado sem validação prematura ou navegação imediata na árvore viva, postergando a resolução do alvo para o momento da execução (`undo`/`redo`).

#### Scenario: Tentativa de criação de comando com mensagem desanexada/órfã
- **WHEN** um comando `CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated` ou `CmdMoverRepeated` for instanciado diretamente com uma instância de mensagem Protobuf que não pertence à árvore do `CroquiModel`
- **THEN** o comando SHALL disparar `ValueError` descrevendo que a mensagem alvo é órfã, impedindo a sua execução e gravação no diário

#### Scenario: Criação de comando legítimo na mensagem raiz ou mensagem filha conectada
- **WHEN** um comando for instanciado para alterar um campo da mensagem raiz `Croqui` ou de uma mensagem filha conectada à árvore (via instância viva ou string de `alvo`)
- **THEN** o comando SHALL ser criado com sucesso, resolvendo o identificador canônico de `alvo` e permitindo execução e serialização normais

#### Scenario: Deserialização de comando com caminho corrompido ou campo inexistente
- **WHEN** o histórico ou diário tentar deserializar um comando cujo caminho/alvo seja inválido ou o campo não exista na mensagem resultante
- **THEN** o sistema SHALL registrar o erro em log e descartar o comando com segurança, permitindo que a recuperação de sessão continue sem travar o editor
- 
#### Scenario: Deserialização declarativa a partir do diário
- **WHEN** o histórico ou diário deserializar um comando a partir dos dados gravados em disco
- **THEN** o comando SHALL ser reconstruído com seu `alvo` (`caminho_msg`) sem navegar imediatamente na árvore do modelo e sem disparar validação prematura de pertencimento

### Requirement: Resolução Tardia de Mensagens Alvo em Comandos Protobuf
Os comandos derivados de `ComandoEditor` que operam sobre mensagens da árvore Protobuf SHALL armazenar e utilizar resolução tardia (*lazy resolution*) através de um identificador de `alvo` em três níveis:
1. **`UID` direto** (ex.: `"esc_1234"`): quando a mensagem possui campo `uid` registrado no `IndiceUidsModel` (ou é a variante ativa de uma `Escalada` com `uid`).
2. **Ancoragem no ancestral mais próximo com `UID` + subcaminho relativo** (ex.: `"setor_abcd.imagens.0"` ou `"esc_1234.via.0.caminho"`): quando a submensagem não possui `uid` próprio, mas descende de uma entidade com `uid`.
3. **Fallback posicional global desde a raiz** (ex.: `"picos.0.imagens.1"` ou `"mapas.0.referencias.2"`): quando nenhum ancestral possui `uid`.

A mensagem alvo viva no modelo SHALL ser resolvida dinamicamente no momento da execução das operações de `undo()` e `executar_redo()`. Caso a mensagem alvo não exista, esteja fora dos limites de repetição ou inacessível, o sistema SHALL tratar a falha através da exceção tipada `MensagemAlvoNaoEncontradaError(LookupError)` ou retorno `None` seguro, abortando a operação sem corromper a árvore.

#### Scenario: Execução de undo com mensagem alvo existente via caminho
- **WHEN** o usuário aciona Desfazer (Undo) em um comando deserializado ou executado previamente cujo `alvo` (`caminho_msg`) é um `UID` (`"esc_1234"`), um subcaminho ancorado em `UID` (`"esc_1234.via.0"`) ou um caminho posicional desde a raiz (`"picos.0"`)
- **THEN** o comando consulta o `IndiceUidsModel` em $O(1)$ (quando ancorado em `UID`) ou navega a partir da raiz `Croqui` pelo `caminho_msg`, localiza a instância viva correspondente e aplica a reversão com sucesso

#### Scenario: Execução de undo com mensagem alvo inexistente ou índice fora de limite
- **WHEN** o usuário aciona Desfazer (Undo) e a mensagem alvo não pode ser resolvida pelo `alvo` (por exemplo, `UID` inexistente, nó excluído ou índice fora dos limites)
- **THEN** o comando SHALL registrar uma mensagem de erro explícita em log reportando a falha de reversão do alvo e não aplicar mutações inconsistentes no modelo

#### Scenario: Navegação segura com tratamento de limites e oneofs inativos
- **WHEN** o sistema navega pela árvore do modelo através de um caminho contendo índices de lista ou seleções de `oneof`
- **THEN** o navegador SHALL verificar os limites de repetição da lista antes de indexar e verificar se a variante do `oneof` está ativa, retornando `None` de forma segura caso o caminho seja inválido em vez de disparar exceções não tratadas

#### Scenario: Despacho de sinal ignora comando com mensagem alvo nula ou não resolvida
- **WHEN** o sistema processa um comando cuja mensagem alvo não pôde ser resolvida no modelo
- **THEN** nenhuma emissão de sinais reativos inconsistentes com identificador nulo SHALL ocorrer

### Requirement: Comandos Compostos Serializáveis (CmdMacro)
O sistema SHALL fornecer a classe `CmdMacro` para agrupar sequências ordenadas de comandos filhos derivados de `ComandoEditor`. O `CmdMacro` SHALL executar os comandos filhos em ordem no `executar_redo()`, em ordem reversa no `undo()`, e propagar `armar_carregamento_silencioso()` para todos os filhos. O `CmdMacro` SHALL implementar métodos `serializar()` e `deserializar()` completos para integração transparente com o `GerenciadorDiario` (`diario_pendente.bin` e `diario_salvo.bin`).

#### Scenario: Execução e reversão de macro
- **WHEN** um `CmdMacro` contendo múltiplos comandos filhos for executado na `QUndoStack`
- **THEN** todos os subcomandos SHALL ser aplicados em ordem no modelo
- **WHEN** o usuário aciona Desfazer (Undo)
- **THEN** todos os subcomandos SHALL ser revertidos em ordem inversa de forma atômica em um único passo da pilha

#### Scenario: Serialização e restauração do diário
- **WHEN** um `CmdMacro` for gravado no `diario_pendente.bin` e posteriormente restaurado via `deserializar_comando`
- **THEN** todos os subcomandos SHALL ser perfeitamente reconstruídos com suas classes e parâmetros originais sem perda de dados

### Requirement: Proibição Arquitetural de Macros Nativos do Qt
O sistema SHALL proibir qualquer chamada direta aos métodos `beginMacro` ou `endMacro` do `QUndoStack` do PySide6 em todo o código-fonte do editor, prevenindo o descarte silencioso de operações pelo diário de persistência. Essa restrição SHALL ser validada de forma automatizada pela suíte de testes de arquitetura.

#### Scenario: Detecção de uso indevido de beginMacro/endMacro
- **WHEN** a suíte de testes de arquitetura (`arquitetura_mvc_test.py`) analisar o código do editor via AST
- **THEN** nenhuma invocação a `beginMacro` ou `endMacro` SHALL ser encontrada
- **WHEN** algum arquivo introduzir chamada a `beginMacro` ou `endMacro`
- **THEN** o teste de arquitetura SHALL falhar imediatamente com mensagem explicativa instruindo o uso de `CmdMacro`

### Requirement: Comandos Atômicos de Buffers em Memória (CmdAlterarImagem e CmdAlterarAnexo)
O sistema SHALL fornecer dois comandos canônicos separados e simétricos em `editor/commands/comandos_protobuf.py` para gerenciar artefatos binários nos buffers em memória RAM do `CroquiModel`:
- `CmdAlterarImagem(model, nome_arquivo, bytes_novos, bytes_antigos=...)`: gerencia a adição (`bytes_antigos=None` -> `bytes_novos=bytes`), substituição (`bytes_antigos=bytes` -> `bytes_novos=bytes`) ou remoção (`bytes_antigos=bytes` -> `bytes_novos=None`) de imagens `.webp` em `_imagens_em_memoria`, emitindo o sinal `imagem_alterada(nome_arquivo)` e aplicando anonimização visual em imagens WebP na serialização de telemetria (`anonimizar=True`).
- `CmdAlterarAnexo(model, nome_arquivo, bytes_novos, bytes_antigos=...)`: gerencia a adição, substituição ou remoção de documentos anexos em `_anexos_em_memoria`.

Ambos os comandos SHALL capturar automaticamente os bytes anteriores presentes no `CroquiModel` caso `bytes_antigos` não seja explicitamente fornecido na instanciação.

#### Scenario: Adição e reversão de imagem no buffer em memória via CmdAlterarImagem
- **WHEN** `CmdAlterarImagem` for executado para registrar uma nova imagem `"foto.webp"` que ainda não existia no `CroquiModel`
- **THEN** o comando captura `bytes_antigos=None`, armazena os novos bytes no buffer `_imagens_em_memoria` e faz o `CroquiModel` emitir `imagem_alterada("foto.webp")`
- **WHEN** o usuário aciona Desfazer (Undo)
- **THEN** o comando remove `"foto.webp"` do buffer `_imagens_em_memoria` e faz o `CroquiModel` emitir `imagem_alterada("foto.webp")`

#### Scenario: Substituição e reversão de anexo no buffer em memória via CmdAlterarAnexo
- **WHEN** `CmdAlterarAnexo` for executado para substituir os bytes de `"guia.pdf"` no `CroquiModel`
- **THEN** o comando retém os bytes anteriores de `"guia.pdf"` e grava os novos bytes em `_anexos_em_memoria`
- **WHEN** o usuário aciona Desfazer (Undo)
- **THEN** os bytes originais de `"guia.pdf"` são integralmente restaurados em `_anexos_em_memoria`

### Requirement: Operações de Alto Nível via Composição em CmdMacro
As operações compostas de alto nível nos Controllers (`CroquiController` e `MapasController`) e nas ferramentas de intenção do servidor MCP (`editor/mcp/ferramentas_comandos.py`) SHALL ser implementadas construindo e empilhando instâncias de `CmdMacro` formadas exclusivamente pelos 6 comandos folha canônicos (`CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem`, `CmdAlterarAnexo`). Isso inclui:
- Alteração de campo de imagem (`CmdAlterarImagem` + `CmdAlterarCampo` + remoção opcional de imagem órfã via `CmdAlterarImagem`).
- Inserção de imagem em Markdown (`CmdAlterarImagem` + `CmdAlterarCampo`).
- Inserção de botão de anexo em Markdown (`CmdAlterarAnexo` + `CmdAlterarCampo`).
- Adição de mapa com arquivo (`CmdAlterarImagem` + `CmdAdicionarRepeated`).
- Alteração em lote de múltiplos itens de lista (`CmdMacro` com múltiplos `CmdAlterarCampo`).
- Migração de setor entre picos (`CmdMacro` contendo `CmdRemoverRepeated` na origem, `CmdAdicionarRepeated` no destino e `CmdAlterarCampo` para reajustar referências ou variantes afetadas).

#### Scenario: Migração de setor executada e desfeita como CmdMacro atômico
- **WHEN** o usuário ou ferramenta MCP invoca a migração de um setor de um pico de origem para um pico de destino
- **THEN** o Controller constrói e empilha um `CmdMacro` contendo a remoção do setor da lista de origem, a inserção no destino e os ajustes de campos de referências/escaladas necessários
- **WHEN** o usuário aciona Desfazer (Undo)
- **THEN** todos os passos do `CmdMacro` são revertidos na ordem inversa em uma única transição atômica, restaurando o setor ao pico e índice originais com seu `UID` intacto

#### Scenario: Alteração de campo de imagem com limpeza de imagem órfã via CmdMacro
- **WHEN** o usuário substitui a imagem de um objeto cuja imagem anterior não é referenciada por mais nenhum item do croqui
- **THEN** o Controller empilha um `CmdMacro` combinando a adição da nova imagem (`CmdAlterarImagem`), a atualização do campo `imagem` (`CmdAlterarCampo`) e a remoção da imagem órfã anterior (`CmdAlterarImagem` com `bytes_novos=None`)
- **WHEN** o usuário aciona Desfazer (Undo)
- **THEN** a imagem anterior é restaurada na memória RAM, o campo volta ao valor antigo e a nova imagem é removida da memória RAM

### Requirement: Isolamento de Comandos Legados para Retrocompatibilidade de Diários
As 12 classes de comando descontinuadas (`CmdAlterarPrimitivo`, `CmdRenomearEscalada`, `CmdAlterarOneof`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdAlterarMetadadosCaminhoNovo`, `CmdAlterarCampoImagem`, `CmdInserirImagemMarkdown`, `CmdInserirBotaoMarkdown`, `CmdAdicionarMapaArquivo`, `CmdSubstituirImagemMemoria`, `CmdMigrarSetor`) SHALL ser isoladas no módulo `editor/commands/comandos_legados.py` e mantidas registradas no despachante `deserializar_comando`. Nenhum código novo de produção ou ferramenta MCP SHALL instanciar essas classes.

#### Scenario: Restauração de diário local contendo comandos legados
- **WHEN** o editor abrir um croqui que possua `diario_pendente.bin` ou `diario_salvo.bin` gravado com qualquer uma das 12 classes de comando legadas
- **THEN** `deserializar_comando` reconstrói a instância correspondente a partir de `editor/commands/comandos_legados.py` e permite ao usuário executar Desfazer (Undo) e Refazer (Redo) normalmente sem perda de histórico

### Requirement: Geração Automática e Determinística de UIDs em Comandos de Adição e Substituição
Os comandos canônicos que introduzem ou substituem mensagens Protobuf na árvore do croqui (`CmdAdicionarRepeated` e `CmdAlterarCampo` nas modalidades de item de lista, `oneof` e submensagem) SHALL garantir automaticamente, no momento de sua instanciação, que toda mensagem ou submensagem com campo `uid` vazio na subárvore recebida receba um NanoID de 14 caracteres antes do congelamento do estado, preservando identificadores pré-existentes em `Undo`, `Redo` e deserialização.

#### Scenario: Adição de entidade sem UID em lista repeated gera NanoID imediatamente
- **WHEN** `CmdAdicionarRepeated` é instanciado e executado com uma mensagem `Escalada`, `Botao`, `PontoDeInteresse`, `SetorOuGrupo` ou `ArquivoSetor` cujo campo `uid` (direto ou em `.conteudo`) está vazio
- **THEN** o comando atribui imediatamente um `uid` NanoID de 14 caracteres à mensagem (e a quaisquer submensagens com `uid` vazio em sua subárvore), congela esse `uid` em `self.valor` e insere a entidade no `CroquiModel`, tornando-a instantaneamente indexada no `IndiceUidsModel`

#### Scenario: Preservação do mesmo UID após ciclos de Undo e Redo
- **WHEN** uma entidade recém-adicionada via `CmdAdicionarRepeated` recebe um `uid` automático, a ação é desfeita (`undo`) e em seguida refeita (`redo`)
- **THEN** a entidade reinserida no `CroquiModel` preserva exatamente o mesmo `uid` gerado na instanciação inicial do comando, mantendo válidas quaisquer referências que apontem para ela

#### Scenario: Preservação de UID pré-existente na instanciação e deserialização
- **WHEN** `CmdAdicionarRepeated` ou `CmdAlterarCampo` é instanciado ou deserializado do diário com uma mensagem que já possui o campo `uid` preenchido
- **THEN** o comando preserva inalterado o `uid` original sem sobrescrevê-lo

#### Scenario: Alteração de variante oneof ou submensagem gera UID quando vazio
- **WHEN** `CmdAlterarCampo` é instanciado para definir ou substituir uma variante de `oneof`, submensagem singular ou item de lista `repeated` cuja nova mensagem possui campo `uid` vazio
- **THEN** o comando preenche automaticamente o `uid` na nova mensagem antes de congelar `valor_novo` e aplica a mutação indexando o novo `uid` no `IndiceUidsModel`

