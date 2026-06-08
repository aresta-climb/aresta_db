## Context

A aplicação que consome o índice dos croquis (aplicativo móvel, website) precisa de dados geográficos para plotar pinos num mapa na visualização geral. O problema é que o `indice.binarypb` hoje só contém os metadados textuais e links para o binário completo do croqui. Isso forçaria os clientes a baixarem todos os croquis do estado/país para exibirem num mapa geral, gerando um custo proibitivo de largura de banda e tempo.
Felizmente, as informações geográficas (latitude e longitude) do ponto inicial de acesso (geralmente o estacionamento) já estão nos arquivos de dados originais (`croqui.yaml` e no `croqui.proto`), armazenadas em tipo `sint32` na notação E7. O presente design detalha como vamos mapear essa informação diretamente para o arquivo de índice.

## Goals / Non-Goals

**Goals:**
- Incluir `latitude` e `longitude` no item `ResumoCroqui` do índice.
- Reaproveitar os dados já existentes em `croqui.yaml` para evitar desincronização.
- Garantir que a geração do índice repasse as coordenadas para o `indice.binarypb` e seu arquivo de debug `indice.yaml`.

**Non-Goals:**
- Modificar o sistema de coordenadas (ex: não vamos alterar para strings ou double point).
- Computar centroides dos picos. Vamos usar especificamente a localização do *primeiro pico* listado no croqui (geralmente o pico principal/estacionamento) como sendo a coordenada do croqui em si.

## Decisions

**1. Reuso da estrutura `Coordenada` importando `croqui.proto`**
- *Opção Escolhida*: Fazer o `indice.proto` importar o `croqui.proto` e usar `Coordenada localizacao = 10;`.
- *Alternativa Considerada*: Copiar e colar a declaração de `message Coordenada { sint32 latitude = 1; ... }` no `indice.proto` para evitar acoplamento.
- *Justificativa*: Como ambos os protos fazem parte do pacote `aresta` da `aresta_api`, utilizar a mesma estrutura garante consistência total (DRY) ao longo de todo o ecossistema e não acarreta problemas reais de dependência, visto que ambos são compilados para as linguagens destino conjuntamente.

**2. Formato E7 `sint32`**
- *Decisão*: Como os YAMLs já têm valores convertidos pelo próprio editor/backend para E7 (ex: `latitude: -198980280`), nós vamos apenas repassar os valores absolutos lidos do dicíonário para os atributos da classe serializada em Python.

## Risks / Trade-offs

- **[Risco] O croqui não ter localização no primeiro pico** → Mitigação: O script de deploy em Python verificará se `picos[0].get("localizacao")` existe; caso não exista, não populará o atributo em `ResumoCroqui`, exigindo tratamento nulo ou valores omitidos do lado do cliente (que é um comportamento normal em protobuf3).
