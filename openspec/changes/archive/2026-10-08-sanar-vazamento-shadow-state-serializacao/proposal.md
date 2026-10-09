# Proposta: Sanar Vazamento de Shadow State na Serialização do Editor

## Why

Identificamos no Sentry um erro crítico em produção (`ValueError: Extensão de Shadow State 'ext_metadados' vazada detectada no arquivo ... database\croqui.yaml`) ao salvar e compilar croquis no Editor Aresta.
Isso ocorre porque extensões Protobuf de *Shadow State* (`ext_metadados_arquivo`), criadas para gerenciar caminhos e estado em memória durante a edição na UI, não são limpas pela rotina de extração e serialização caso a entidade não possua o campo `conteudo` populado (por exemplo, quando possui apenas `caminho` ou quando se trata de `mapas_gerais` referenciado/editado na árvore), fazendo com que o `MessageToDict` gere chaves com formato `'[aresta.*.ext_metadados_arquivo]'` diretamente no `croqui.yaml` e viole a trava de segurança do deploy (`validar_sem_extensoes_vazadas`).

## What Changes

- **Limpeza Incondicional e Defensiva de Extensões de Shadow State**: Garantir que `CroquiModel.extrair_arquivos_e_serializar` remova e limpe incondicionalmente a extensão `ext_metadados_arquivo` de todas as mensagens conhecidas (`Croqui`, `ArquivoMapas`, `ArquivoSetor`, `ArquivoGrupo` e `ArquivoMarkdown`), independentemente de o campo `conteudo` estar preenchido ou de a entidade possuir apenas `caminho`.
- **Sanitização Recursiva de Dicionários Serializados**: Implementar rotina pura de sanitização recursiva que remove sumariamente quaisquer chaves que contenham `ext_metadados` ou iniciem com colchetes `[` antes de gravar o `croqui.yaml` ou o frontmatter dos arquivos `.md`.
- **Prevenção de Efeitos Colaterais em `_carregar_arquivo_*`**: Garantir que falhas de parser ou conteúdos vazios em arquivos externos não deixem extensões de shadow state associadas a mensagens que permanecem apenas com `caminho`.
- **Testes de Regressão e Contrato**: Expandir a suíte de testes de contrato de serialização (`contrato_editor_serializacao_test.py`) e unitários para cobrir todas as 5 entidades com extensões configuradas, atestando conformidade estrita com `validar_sem_extensoes_vazadas`.

## Capabilities

### New Capabilities
- `editor-serializacao-croqui`: Define o contrato de serialização do editor no disco, garantindo persistência atômica, ordenação determinística e isolamento estrito de extensões e metadados de shadow state para que nunca vazem em `croqui.yaml` ou arquivos Markdown.

### Modified Capabilities
<!-- Nenhuma especificação de comportamento funcional existente é modificada; o isolamento estrito do shadow state passa a ser governado pela nova capacidade. -->

## Impact

- `editor/models/croqui_model.py`: limpeza defensiva de extensões e sanitização recursiva em `extrair_arquivos_e_serializar` e `_salvar_objeto_com_frontmatter`.
- `tests/contrato_editor_serializacao_test.py`: novos cenários de teste de contrato garantindo 100% de cobertura e blindagem contra vazamento de shadow state.
- Estabilidade e deploy: eliminação de falhas de compilação pós-salvamento no canal Beta do Editor Aresta.
