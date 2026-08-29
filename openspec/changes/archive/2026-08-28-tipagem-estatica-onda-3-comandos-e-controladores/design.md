# Design Técnico: Onda 3 - Tipagem Estática de Comandos e Controladores

## Arquitetura e Estratégia de Tipagem

A camada de comandos e controladores reside entre o núcleo de dados (\ditor/core/\) e a camada de visualização (\ditor/views/\), funcionando como o orquestrador de regras de negócio e mutações do modelo Protobuf.

\\\
┌────────────────────────────────────────────────────────┐
│                   Camada de Views                      │
└──────────────────────────┬─────────────────────────────┘
                           │ (Sinais / Chamadas)
                           ▼
┌────────────────────────────────────────────────────────┐
│             Controladores (editor/controllers/)        │
│  - CroquiController, MapasController,                  │
│    CompilacaoController, PublishController             │
└──────────────────────────┬─────────────────────────────┘
                           │ (QUndoStack / QUndoCommand)
                           ▼
┌────────────────────────────────────────────────────────┐
│              Comandos (editor/commands/)               │
│  - CmdAlterarPrimitivo, CmdAdicionarRepeated,          │
│    CmdAlterarOneof, Cmds de POIs e Mapas               │
└──────────────────────────┬─────────────────────────────┘
                           │ (Mutações Diretas / Protobuf)
                           ▼
┌────────────────────────────────────────────────────────┐
│               Modelos Protobuf & Core                  │
│  - Croqui, Indice, CoordenadasE7, Diário               │
└────────────────────────────────────────────────────────┘
\\\

---

## Decisões Técnicas

### 1. Comandos Protobuf e Classes de Mutação
- Em \ditor/commands/comandos_protobuf.py\, cada comando herda de \QUndoCommand\.
- Tipar expressamente os atributos de mensagem (\msg: google.protobuf.message.Message\), campos de nome (\campo_nome: str\), índices de coleções repetidas (\index: int\) e valores antigos/novos (\alor_antigo: Any\, \alor_novo: Any\).
- Anotar com precisão os métodos de serialização (\serializar(self, anonimizado: bool = False) -> dict[str, Any]\) e a factory global de deserialização (\deserializar_comando(dados: dict[str, Any], raiz_modelo: Any) -> QUndoCommand\).

### 2. Comandos de Mapas e Pontos de Interesse (POIs)
- Em \ditor/commands/comandos_mapas.py\, comandos como adição, deleção, movimentação e edição de nós de mapa devem receber coordenadas tipadas (\loat\, \int\ ou \CoordenadasE7\) e referências estritas ao croqui ativo.

### 3. Controladores e Sinais PySide6
- Todos os controladores herdam de \QObject\.
- Todos os sinais de classe (\Signal\) devem explicitar os tipos dos argumentos emitidos (ex: \Signal(bool)\, \Signal(str, str)\, \Signal(object)\).
- Construtores de controladores devem aceitar parâmetros tipados com suporte opcional a injeção de dependências (facilita testes unitários desacoplados).

### 4. Preservação de Compatibilidade de Diário
- Garantir que dicionários gerados pelas rotinas de serialização de comandos permaneçam 100% retrocompatíveis com os arquivos \diario_salvo.bin\ e \diario_pendente.bin\ em disco.

---

## Plano de Validação
- **MyPy Estrito**: 0 erros em \ditor/commands/\, \ditor/controllers/\ e \ditor/build.py\.
- **AST Validator**: 100% de cobertura de assinaturas e retornos.
- **Suíte de Testes**: Validação com Pytest de todos os testes unitários da suíte.
