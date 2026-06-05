## Context

O editor Aresta DB carrega YAMLs do disco que contêm marcações `caminho` (referenciando um Markdown) ou `conteudo` (referenciando texto inline). Esses campos existem mutuamente exclusivos num block `oneof arquivo { ... }` dentro de `ArquivoMarkdown`, `ArquivoSetor` e `ArquivoGrupo`.
Devido a essa característica estrita do Protobuf, sempre que a UI do editor modifica o texto, o Protobuf apaga internamente a string original do caminho (porque setou a string `conteudo`). Sem saber de onde esse texto veio, o editor foi historicamente acoplado com DICIONÁRIOS PARALELOS (`caminhos_originais`, `arquivos_carregados`) de gerenciamento manual. Isso resultou em alta fragilidade, vazamento de abstração e impossibilidade de deleção consistente do arquivo antigo caso seu nome ou seu conteúdo fosse reescrito.

## Goals / Non-Goals

**Goals:**
- Centralizar o estado do caminho de origem do Arquivo puramente dentro da instância Protobuf.
- Eliminar por completo os rastreadores de estado e referências (`arquivos_carregados`, `caminhos_originais`) do `widget_editor_dados.py` e `area_principal.py`.
- Apagar do disco o arquivo markdown prévio quando ele não for mais utilizado ou se for renomeado.
- Permitir edição inline no editor sem corromper a leitura.

**Non-Goals:**
- Mudar a API final do protoc/YAML (O YAML final manterá a integridade com ou sem a presença do Shadow State).
- Migrar repositório de binários das imagens.

## Decisions

**1. Shadow State via Extensões no Protobuf:**
Criaremos extensões protobuf na message raiz para armazenar em runtime informações descartáveis (`caminho_original` e `caminho_novo`). Escolhemos Option A (Extensões Puras) ao invés de Option B (Campos ocultos nativos) pois assim definimos metadados que podem ser injetados ou apagados programaticamente em Python através de `obj.Extensions[ext]`, mantendo a assinatura original da mensagem limpa e compatível.
*Decisão Final:* Usar a opção A para adicionar extensões de escopo do editor `aresta.caminho_original` e `aresta.caminho_novo`.

**2. Lógica de Load (Parse / Deserialize) e ReadOnlyProxy:**
O `CroquiModel` (ou durante o load em memória do Editor), antes de qualquer modificação, populam ambas extensões (`caminho_original` e `caminho_novo`) com o valor lido do `caminho` inicial, mantendo referências estáveis. O campo original `caminho` é então esvaziado pelo Protobuf ao injetarmos a string na chave `conteudo` para forçar sua renderização na UI. Adicionalmente, como o editor força uma arquitetura rigorosa de MVC, o componente `ReadOnlyProxy` precisará ser atualizado para envelopar a propriedade `.Extensions` do Protobuf num proxy de leitura, garantindo que a UI apenas leia as extensões, sem mutá-las diretamente (mutações sempre passarão por Comandos).

**3. Lógica de Save (Serialize / IO):**
No momento de interceptar a submissão no `CroquiModel` (antes de serializar via JSON/YAML):
Se `conteudo` existir no Protobuf:
a. Checa `caminho_novo`. Se vazio, ignora salvamento em disco e assume-se texto inline final.
b. Caso contrário, grava o `conteudo` em disco em `caminho_novo`.
c. Se `caminho_original` existir no disco, for acessível, e for diferente de `caminho_novo`, aciona deleção do `caminho_original` do disco.
d. Seta o campo real `caminho` do protobuf para `caminho_novo`, removendo o texto de `conteudo`.
e. Limpa as propriedades da extensão (ClearExtension).

## Risks / Trade-offs

- **[Risco] Python Protobuf Extensions podem ser crípticas de acessar:** Requerem importação do protobuf schema e uso de notação de dicionário `obj.Extensions[caminho_original]`. → *Mitigação*: Criar métodos utilitários no `CroquiModel` para facilitar o wrap da UI e extrair o boilerplate.
- **[Risco] Deleção Indesejada de Arquivos Compartilhados:** A heurística assume que o `caminho_original` era posse única dessa mensagem. Se duas partes da UI referenciaram o mesmo MD, a renomeação em uma deletaria o MD da outra. → *Mitigação*: O sistema `preparar_submissao_lib.py` já foi estendido para duplicar referências idênticas nos metadados, minimizando dependências cruzadas e mantendo referências únicas 1:1. O Garbage Collector do Croqui varrerá qualquer resíduo remanescente.
