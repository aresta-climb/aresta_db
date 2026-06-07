## Context

O ciclo de vida de um croqui experimental (no repositório de edição local) envolve salvamentos constantes na interface gráfica associados com a orquestração da estrutura no disco. O gerenciamento de diretórios baseia-se no ID do croqui (`<timestamp>_<id>`). Ao alterar o ID do croqui na UI, o vínculo do sistema de arquivos com os metadados internos — bem como a correspondência no momento do push para a ramificação remota no Github (`database/<id>`) — era quebrado. O usuário acabava com a pasta antiga preservada sem intenção no repo remoto quando o Pull Request era publicado, resultando numa duplicação permanente no banco de dados.

## Goals / Non-Goals

**Goals:**
- Manter o diretório físico perfeitamente sincronizado com o novo ID assim que a interface enviar o comando de "Salvar".
- Estabelecer uma capacidade no worker de publicação (`TarefaPublicacao`) para saber qual era o ID base/ancestre do projeto experimental.
- Transmitir a deleção do ID velho para o repositório oficial (`git rm`) durante o empacotamento do Pull Request.

**Non-Goals:**
- Não reestruturaremos a estrutura principal do Protobuf base (`croqui.proto`) para suportar um histórico encadeado de re-identificações, visto que um simples campo acessório no YAML de metadados experimentais local (`croqui_experimental.yaml`) é plenamente suficiente.

## Decisions

1. **Atributo Âncora**: Optamos por salvar um campo `id_original` dentro de `croqui_experimental.yaml` logo no momento de inicialização ou clonagem. Esta solução é leve e se aproveita do arquivo que já existe puramente para rastrear metadados privados da edição, não sujando o banco final com rastros do editor.
2. **Separação de Responsabilidade**: Decidimos não adicionar a lógica de renomeação na UI nem no `worker.py`, mas sim um método `renomear_pasta_croqui` dentro do `GerenciadorCroquiExperimental`. A view apenas injeta o comando, e o worker apenas lê o resultado lógico.
3. **Mecanismo Anti-Lock no OS**: Optou-se por introduzir *retries* ao tentar invocar a renomeação da pasta do SO (com fallback para `shutil.move`), blindando possíveis travamentos de processo pelo Windows Defender ou visualizadores de sistema durante a renomeação.

## Risks / Trade-offs

- **[Risk] Path References em Cache da Interface** → Ao renomear a pasta raiz abruptamente, componentes complexos (como o mapa e o visualizador de imagens) da UI podem ainda conter uma string de *Path* cacheados do `id_antigo`, levando-os a escrever arquivos no vazio ou gerar crashes. 
  - **Mitigação**: O rename é realizado numa camada da view principal `salvar_croqui` onde o ponteiro central de `self.caminho_croqui` é imediatamente subscrito. Os componentes filhos da interface só realizam o sync para o disco nos comandos subsequentes e são todos relativos ao novo `self.caminho_croqui`.
