## Context

Ver `proposal.md` para motivação e problemas identificados.

Esta especificação técnica é guiada estritamente pelos **Princípios de Engenharia Aresta (`AGENTS.md`)**:
- **I. Tudo em Português**: Toda a terminologia, documentação, especificações, nomes de módulos, classes, métodos e variáveis são estritamente em português brasileiro.
- **II. Library-First (Biblioteca em Primeiro Lugar)**: As regras de identificação de imagens órfãs e de deduplicação de nomes de arquivos são desacopladas da interface gráfica e implementadas como bibliotecas puras, autossuficientes e testáveis em `editor/core/`.
- **III. 100% de Unit Test Coverage**: Todos os arquivos novos e modificados contarão com cobertura integral de testes unitários.
- **IV. Imperativo do Teste em Primeiro Lugar (TDD)**: O fluxo Vermelho-Verde-Refatorar guiará cada etapa da implementação.
- **V. Testes de Integração em Primeiro Lugar**: A suíte de integração de ponta a ponta é estabelecida antes dos testes unitários profundos dos componentes.
- **VI. Simplicidade e Anti-Abstração**: Funções puras, diretas e declarativas, evitando fábricas ou hierarquias desnecessárias.
- **VII. Edições de Estado via Comandos do Histórico (Undo/Redo)**: O descarte e a restauração de imagens em memória RAM ocorrem exclusivamente pelo ciclo de vida de `QUndoCommand` (`CmdRemoverRepeated`) na pilha global de histórico.

## Goals / Non-Goals

**Goals:**
- Criar a biblioteca pura [`editor/core/imagens_croqui.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/imagens_croqui.py) com funções independentes para extração de referências de imagens e cálculo de imagens órfãs em remoções.
- Criar a biblioteca pura [`editor/core/nomes_arquivos.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/nomes_arquivos.py) para deduplicação consistente de prefixos (`setor_`, `grupo_`) e sugestão padronizada de nomes de arquivos.
- Fazer com que `CmdRemoverRepeated` limpe da memória RAM imagens que se tornem órfãs após a exclusão do elemento (seja ele um Mapa, Setor, Grupo ou Pico), e as restaure caso a ação seja desfeita (`undo`).
- Corrigir a validação no `DialogoAdicionarMapa` para consultar especificamente o buffer de memória RAM (`obter_imagens_em_memoria`), eliminando falsos positivos de arquivos existentes no disco.
- Estabelecer teste de integração de ponta a ponta cobrindo o fluxo de adição, remoção, re-adição e Undo/Redo antes dos testes granulares.

**Non-Goals:**
- Não apagar arquivos físicos preexistentes na pasta `imagens/` do disco ao remover mapas.
- Não alterar a escrita física tardia no disco, que continua ocorrendo em `CroquiModel.extrair_arquivos_e_serializar`.

## Decisions

### Decisão 1 (Library-First): Biblioteca Pura `editor/core/imagens_croqui.py`
Para não inflar a camada de comandos nem acoplar a lógica de inspeção de Protobuf à interface:
- **`extrair_caminhos_imagens(msg: Any) -> list[str]`**: Percorre recursivamente uma mensagem Protobuf (ou proxy) inspecionando campos de imagem (`caminho_imagem_mapa`, `caminho_thumbnail`).
- **`obter_imagens_orfas_ao_remover(croqui_raiz: Any, item_removido: Any, imagens_em_ram: dict[str, bytes]) -> dict[str, bytes]`**:
  - Conta a frequência de cada caminho de imagem no croqui completo e no item a ser removido.
  - Se todas as ocorrências de um determinado caminho pertencem ao item removido e esse caminho está no buffer de RAM, esse caminho e seus respectivos bytes são retornados como órfãos.
- Arquivo acompanhado obrigatoriamente de [`editor/core/imagens_croqui_test.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/imagens_croqui_test.py) com 100% de cobertura.

### Decisão 2 (Library-First): Biblioteca Pura `editor/core/nomes_arquivos.py`
Centraliza as regras de higienização e deduplicação de nomes:
- **`deduplicar_prefixo(nome: str, prefixo: str) -> str`**: Converte o nome para snake_case e garante que o prefixo (e.g. `setor_` ou `grupo_`) não seja duplicado caso o nome original já o contenha.
- **`gerar_nome_mapa_sugerido(entidade: Any, indice: int) -> str`**: Determina o prefixo conforme o tipo de entidade pai (`setor`, `grupo` ou mapas gerais) e produz o nome no formato `{base}_p{indice}.webp`.
- **`gerar_nome_arquivo_entidade(nome: str, tipo: str) -> str`**: Gera a proposição `{base}.md` sem duplicação (e.g. `setor_fugitivos_i.md`).
- Arquivo acompanhado obrigatoriamente de [`editor/core/nomes_arquivos_test.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/nomes_arquivos_test.py) com 100% de cobertura.

### Decisão 3 (Histórico & Undo/Redo): Integração no `CmdRemoverRepeated`
- No `__init__`, utiliza `obter_imagens_orfas_ao_remover` para capturar `{caminho: bytes}` em `self.imagens_removidas_ram`.
- No `executar_redo()`: remove o item do Protobuf e executa `model.remover_imagem_memoria(caminho)` para cada imagem órfã.
- No `undo()`: reinseri o item no Protobuf e executa `model.definir_imagem_memoria(caminho, bytes)` para cada imagem restaurada.
- Na serialização e deserialização do comando, preserva `imagens_removidas_ram` para manter a integridade do diário de recuperação (`diario_pendente.bin`).

### Decisão 4: Validação Exata em `DialogoAdicionarMapa`
- Substitui `model.obter_bytes_imagem(caminho_rel)` por `caminho_rel in model.obter_imagens_em_memoria()`.
- Garante separação nítida:
  1. Conflito em RAM: alerta de memória RAM.
  2. Conflito em Disco: alerta da pasta `imagens/`.
  3. Nome livre após remoção: liberado sem bloqueios.

## Risks / Trade-offs

- **[Risco] Imagens compartilhadas entre múltiplos mapas**: Um mapa removido não pode apagar da RAM uma imagem utilizada por outro mapa ativo.
  - *Mitigação*: A função `obter_imagens_orfas_ao_remover` verifica a contagem de referências global no croqui, descartando da memória apenas quando não houver nenhum outro consumidor no croqui.
- **[Risco] Histórico gravado no Diário Pendente**: Persistência do comando em disco sem perda dos bytes da imagem.
  - *Mitigação*: O dicionário `imagens_removidas_ram` é serializado com suporte opcional a anonimização (`gerar_webp_anonimizado`).
