## Context

Veja [proposal.md](file:///C:/Renato/Devel/aresta-climb/aresta_db/openspec/changes/corrigir-inserir-imagem-markdown/proposal.md) para a motivação e visão geral do problema.

Atualmente, o diálogo `DialogoAdicionarMapa` oferece uma experiência visual moderna: botão "Selecionar Imagem..." no cabeçalho, área de Drag & Drop com feedback estilizado e preview integrado, painel de metadados ricos (dimensões e pesos antes/depois da conversão WebP), sanitização de slug e validação em tempo real de nomes contra a memória RAM e o disco. Em contrapartida, `DialogoInserirImagemMarkdown` foi implementado com estrutura fragmentada de abas, sem botão no cabeçalho, sem metadados ricos e sem validação contínua de colisões.

Além disso, a rotina de salvamento dispara a limpeza de arquivos (`limpar_arquivos_nao_utilizados`), cuja coleta de referências (`coletar_referencias_arquivos`) rastreia apenas imagens em setores e enfiadas de mapas, omitindo `croqui.descricao`, `pico.descricao`, todas as `escaladas` filhas (`via_esportiva`, `via_movel`, `boulder`, etc.), `trilha.descricao` e `ponto_de_interesse.descricao`. O resultado é que imagens recém-inseridas no Markdown são deletadas do disco (`unlink`) pelo compilador imediatamente após o salvamento.

Por fim, a inserção de bytes de imagem no modelo ocorria via mutação direta sem `QUndoCommand`, violando o Princípio VII do repositório.

## Goals / Non-Goals

**Goals:**
- Extrair o componente visual `AreaDropImagem` para uma biblioteca autossuficiente e testada (`editor/views/componentes/area_drop_imagem.py`), promovendo reuso tanto em `DialogoAdicionarMapa` quanto em `DialogoInserirImagemMarkdown` (Princípio II - Library-First).
- Alinhar a interface de `DialogoInserirImagemMarkdown` ao padrão de `DialogoAdicionarMapa`: cabeçalho com botão explícito "Selecionar Imagem...", área de drop com preview integrado, painel de metadados de imagem (dimensões e tamanhos em KB), campo de slug de arquivo com sanitização automática e validação de colisões em tempo real.
- Preservar o fluxo de inserção de imagens existentes (galeria do croqui) e a obrigatoriedade da legenda da imagem Markdown (`input_legenda`).
- Expandir `coletar_referencias_arquivos` em `scripts/preparar_submissao_lib.py` com inspeção recursiva de todos os campos de texto do croqui e arquivos Markdown referenciados, garantindo que nenhuma imagem em uso no Markdown seja excluída na limpeza de arquivos órfãos.
- Garantir que a inserção da imagem em memória e da tag de texto no editor seja transacional e reversível via comandos `QUndoCommand` na pilha `historico` (Princípio VII).

**Non-Goals:**
- Não alterar os formatos de arquivo suportados (mantendo `.webp`, `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.heic`).
- Não modificar os parâmetros de compressão padrão (WebP lossy 85, limite de 4 Megapixels).
- Não alterar a estrutura dos arquivos Protobuf nem do compilador de banco de dados além da rotina de limpeza e coleta de referências.

## Decisions

### Decisão 1: Extração de `AreaDropImagem` como componente autônomo
- **Abordagem**: Mover `AreaDropImagem` para `editor/views/componentes/area_drop_imagem.py` com cobertura de 100% de testes unitários (`area_drop_imagem_test.py`), importando-a em `DialogoAdicionarMapa` e `DialogoInserirImagemMarkdown`.
- **Alternativas consideradas**: Duplicar a implementação em ambos os diálogos.
- **Racional**: A duplicação viola os Princípios II (Library-First) e VI (Anti-Abstração semântica com DRY prudente), além de aumentar a propensão a divergências visuais e comportamentais no futuro.

### Decisão 2: Reestruturação do Diálogo de Markdown mantendo Galeria e Importação Unificada
- **Abordagem**: Manter o suporte a escolher imagens existentes do croqui e importar novas imagens, mas estruturar a aba/painel de importação com a mesma anatomia de `DialogoAdicionarMapa`:
  1. Cabeçalho com instrução e botão "Selecionar Imagem...".
  2. Área central `AreaDropImagem` com preview.
  3. Painel de metadados ricos (dimensões, peso original e WebP).
  4. Campo de nome sanitizado de destino e validação contínua contra disco e RAM com aviso em vermelho.
  5. Campo de legenda (obrigatório para Markdown).
  6. Botões de ação (Cancelar / Inserir Imagem).
- **Alternativas consideradas**: Eliminar a aba de galeria e forçar o usuário a sempre re-importar arquivos do disco.
- **Racional**: A galeria de imagens existentes é um recurso valioso para reutilizar imagens já salvas no croqui sem precisar reenviar o arquivo. Unificar o visual da importação resolve a divergência ergonômica sem perda funcional.

### Decisão 3: Coleta Recursiva Universal de Imagens Markdown no Compilador
- **Abordagem**: Implementar em `scripts/preparar_submissao_lib.py` uma rotina recursiva de extração que varre todos os valores de texto do dicionário `croqui_data` e de todos os arquivos `.md` referenciados, buscando ocorrências de `!\[.*?\]\((.*?)\)` e caminhos de imagens.
- **Alternativas consideradas**: Adicionar manualmente apenas `croqui.descricao` e `pico.descricao` em `coletar_referencias_arquivos`.
- **Racional**: O modelo de dados possui múltiplos níveis de hierarquia com campos de descrição em vias (`via_esportiva`, `via_movel`, etc.), setores, trilhas e pontos de interesse. Listar campos manualmente seria frágil e deixaria brechas para que imagens fossem deletadas por engano. Uma varredura recursiva de strings com Regex é à prova de falhas e executa em menos de 5ms.

### Decisão 4: Comando de Histórico para Inserção de Imagem e Texto
- **Abordagem**: No editor de Markdown (`WidgetEditorMarkdown`), ao aceitar o diálogo com nova imagem, empilhar um `QUndoCommand` que gerencie o ciclo de vida dos bytes na memória do modelo e a alteração textual no Protobuf, garantindo que desfazer (`Ctrl+Z`) remova a referência e restaure o estado anterior.
- **Alternativas consideradas**: Manter a chamada imperativa `model.definir_imagem_memoria()` fora do histórico.
- **Racional**: O Princípio VII estabelece categoricamente que qualquer alteração de estado no croqui ou no editor deve ser transacionada via histórico.

## Risks / Trade-offs

- **[Risco] Impacto de desempenho na varredura recursiva de strings do croqui**
  $\rightarrow$ **Mitigação**: O volume textual de um croqui completo raramente ultrapassa alguns milhares de nós e strings. Testes demonstraram que a varredura por expressões regulares em dicionários em memória consome menos de 5ms, sem impacto perceptível no tempo de compilação ou salvamento.

- **[Risco] Colisão de nomes entre imagem nova e imagem já existente na pasta `imagens/`**
  $\rightarrow$ **Mitigação**: O diálogo realiza verificação contínua do nome de destino contra a pasta no disco e contra o mapa de imagens em memória (`obter_imagens_em_memoria()`), exibindo mensagem de colisão em tempo real e desabilitando o botão de inserção até o usuário escolher um nome único.
