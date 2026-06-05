## Contexto

A `TelaDeCarregamento` foi implementada como um protótipo visual. A lógica de manipulação de croquis experimentais já existe na biblioteca `GerenciadorCroquiExperimental`, mas não está conectada à interface. Além disso, a funcionalidade de editar um croqui oficial requer a criação de um novo componente de interface para busca e seleção.

## Objetivos / Não-Objetivos

**Objetivos:**
- Conectar os botões da tela de carregamento às funções do `GerenciadorCroquiExperimental`.
- Implementar o diálogo de busca de croquis oficiais.
- Permitir a criação de croquis experimentais a partir de croquis oficiais.
- Garantir que a lista de histórico seja atualizada dinamicamente.

**Não-Objetivos:**
- Implementar a tela de edição propriamente dita (apenas disparar a abertura).
- Implementar sincronização remota (Git remoto) nesta etapa.

### 2. Feedback de Operações e Compilação
Em vez de um `QProgressDialog` genérico, foi implementado o `DialogoProgressoLog`. Este diálogo:
- Captura o `stdout` em tempo real para exibir logs detalhados da operação (cópia, importação e compilação).
- Fecha automaticamente em caso de sucesso para agilizar o fluxo do usuário.
- Permanece aberto em caso de falha para que o usuário possa inspecionar o erro.

### 3. Resiliência e Integridade de Dados
Para evitar estados corrompidos no storage local:
- **Limpeza Automática**: Em caso de falha durante a criação ou importação, a pasta parcial é removida automaticamente.
- **Normalização de ZIP**: O processo de importação detecta e "achata" estruturas aninhadas (pastas raiz extras) comuns em arquivos compactados.
- **Git Automático**: Se um croqui for importado sem histórico, o sistema inicializa automaticamente um repositório Git local para habilitar o controle de versões.

### 4. Layout Responsivo e UX
- **Ordenação**: A lista de histórico é ordenada de forma decrescente pela data da última edição (timezone-aware).
- **Redimensionamento**: A janela é totalmente responsiva e maximizável, utilizando `QVBoxLayout` com fatores de expansão (stretch) para priorizar a visualização da lista de histórico em telas grandes.
- **Resiliência Windows**: Implementação de loops de tentativa (retry) para operações de arquivo (rename/remove) para lidar com locks temporários do SO.

### 3. Gerenciamento de Estado e Sinais
A `TelaDeCarregamento` emitirá sinais ou chamará callbacks quando um croqui for selecionado ou criado, permitindo que a `MainWindow` (em `main.py`) feche o diálogo e abra o editor.

## Riscos / Trade-offs

- **[Risco] Performance de Busca** → Com muitos croquis, scanear o disco a cada abertura pode ser lento. *Mitigação*: Utilizar o arquivo `aresta_db/generated/indice.binarypb` para leitura rápida dos dados dos croquis.
- **[Trade-off] Cópia de Imagens** → Ao editar um croqui oficial, copiar todas as imagens pode consumir espaço e tempo. *Mitigação*: É necessário para portabilidade; um `QProgressDialog` será usado para manter o usuário informado durante o processo.
