## MODIFIED Requirements

### Requirement: Editor release automation
O sistema DEVE (SHALL) compilar e publicar o executável do editor mediante acionamento manual em um ambiente de dependências isolado, etiquetando a versão com a numeração semântica fornecida e garantindo que o tamanho do binário permaneça estritamente dentro dos limites de otimização (< 95MB).

#### Scenario: User triggers the workflow
- **WHEN** um mantenedor do repositório disparar o fluxo de trabalho de lançamento informando uma versão semântica válida
- **THEN** o sistema compila o executável para Windows utilizando o ambiente isolado do grupo `editor`, cria uma Release no GitHub anexada à nova tag do git, e faz o upload do arquivo `.exe` otimizado
