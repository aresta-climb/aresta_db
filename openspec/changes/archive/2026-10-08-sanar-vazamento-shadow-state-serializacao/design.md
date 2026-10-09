# Design: Sanar Vazamento de Shadow State na Serialização do Editor

## Context

O Editor Aresta utiliza o mecanismo de extensões Protobuf (`ext_metadados_arquivo`) como *Shadow State* em memória para rastrear caminhos de arquivos (`caminho_original` e `caminho_novo`) e JSONs originais de frontmatter durante a edição na interface gráfica.

Ao persistir o croqui no disco, o método `CroquiModel.extrair_arquivos_e_serializar` cria uma cópia da mensagem em memória (`croqui_msg_copy = Croqui(); croqui_msg_copy.CopyFrom(self.__croqui)`), extrai os conteúdos das entidades filhas (`pico.mapas_gerais`, `setor`, `grupo`, `botao`) em arquivos Markdown separados e, ao final, converte a mensagem raiz para dicionário através de `MessageToDict(croqui_msg_copy)` para gerar o `croqui.yaml`.

Atualmente, a rotina de extração só processa e limpa a extensão (`ClearExtension`) dos wrappers de arquivo se o campo `conteudo` estiver ativo (ex.: `if pico.HasField("mapas_gerais") and pico.mapas_gerais.HasField("conteudo"):`). Caso o elemento possua apenas o campo `caminho` (por exemplo, quando `mapas_gerais` é referenciado ou editado na árvore sem mapas inline, ou quando um setor/grupo é referenciado externamente e seu conteúdo falha ao carregar), a extensão `ext_metadados_arquivo` nunca é limpa da mensagem cópia. Quando `MessageToDict` é executado, o Protobuf serializa extensões não limpas como chaves do tipo `'[aresta.ArquivoMapas.ext_metadados_arquivo]'`, que são salvas no `croqui.yaml` e violam a regra de integridade `validar_sem_extensoes_vazadas` do deploy.

## Goals / Non-Goals

**Goals:**
- Garantir que `croqui.yaml` e quaisquer arquivos `.md` gravados pelo editor nunca contenham chaves ou vestígios de extensões de shadow state (`ext_metadados`).
- Realizar a limpeza incondicional das extensões em `croqui_msg_copy` para todos os nós de arquivo (`mapas_gerais`, `setores_ou_grupos`, `setores` internos, `botoes` e na própria raiz `Croqui`), independentemente de possuírem `conteudo` ou apenas `caminho`.
- Adicionar uma camada de defesa em profundidade através de sanitização recursiva de dicionários antes da gravação em disco.
- Manter 100% de cobertura de testes unitários e de integração (Princípio III e IV).

**Non-Goals:**
- Não alterar a definição do schema Protobuf (`croqui.proto`) nem o uso legítimo das extensões de shadow state em memória na interface.
- Não desativar ou afrouxar a validação `validar_sem_extensoes_vazadas` no pipeline de deploy (`scripts/deploy_generated.py`), que permanece como a salvaguarda canônica.

## Decisions

### Decisão 1: Defesa em Profundidade (Limpeza no Protobuf + Sanitização no Dicionário)

Optamos por aplicar duas camadas complementares de proteção:
1. **Camada Protobuf**: No método `extrair_arquivos_e_serializar`, varrer incondicionalmente todos os containers (`mapas_gerais`, `setores_ou_grupos`, `setores` internos de grupos e `botoes`) e chamar `ClearExtension` mesmo quando o nó contiver apenas `caminho` ou estiver vazio. Além disso, invocar `croqui_msg_copy.ClearExtension(Croqui.ext_metadados_arquivo)` incondicionalmente no root.
2. **Camada Dicionário**: Implementar a função utilitária pura `sanitizar_dicionario_sem_extensoes(dados)` que remove recursivamente qualquer chave que inicie com `[` ou contenha `ext_metadados` antes de serializar o YAML ou salvar os frontmatters.

*Alternativas consideradas*:
- *Apenas limpeza no Protobuf*: Deixaria o sistema vulnerável a novas entidades adicionadas futuramente no schema que esqueçam de ser tratadas no loop de extração.
- *Apenas sanitização no dicionário*: Resolveria a gravação no disco, mas deixaria o objeto Protobuf cópia poluído em memória durante a rotina.
*Razão*: A combinação garante consistência semântica interna e blindagem infalível contra vazamentos em arquivos.

### Decisão 2: Função Pura em Biblioteca (Library-First)

A lógica de sanitização de dicionários será implementada como função pura em `editor/core/serializacao_util.py` (ou integrada nas rotinas puras de serialização), operando em cópias de dicionários e listas de forma recursiva, testável de maneira isolada sem depender de UI ou arquivos físicos.

### Decisão 3: Tratamento de Falhas de Carregamento Externo

Em `CroquiModel.carregar_arquivos_externos`, se um arquivo externo `.md` for inexistente, vazio ou corrompido, a rotina não deve deixar extensões residuais pendentes na mensagem caso o campo `conteudo` não tenha sido povoado com sucesso.

## Risks / Trade-offs

- **[Risco] Mutação acidental de chaves válidas na sanitização** → *Mitigação*: O filtro de remoção atua estritamente em chaves que começam com o caractere `[` (formato exclusivo de extensões Protobuf via `MessageToDict`) ou contenham `"ext_metadados"`. Chaves regulares do domínio (como `id`, `uid`, `nome`, etc.) não são afetadas.
- **[Risco] Alteração na ordenação de campos do YAML** → *Mitigação*: A sanitização preserva a ordem de iteração dos dicionários Python 3.7+ (`dict` ordenado), aplicando-se sobre o dicionário resultante após a etapa de `_reordenar_recursivamente`.
