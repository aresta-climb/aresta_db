---
name: converter_parte_croqui_para_markdown
description: Converte uma parte de um croqui diretamente para a árvore Protobuf do Editor Aresta via MCP em transação atômica por UID.
---

# Converter Parte de Croqui para a Árvore Protobuf via MCP

Nesta skill, você recebe os metadados de uma parte específica do croqui já particionada por `aresta_particionar_pdf_croqui`:
- `id_croqui`: Identificador do croqui aberto no Editor Aresta.
- `nome_parte`: Chave da parte (ex: `"capa"`, `"introducao"`, `"mapas_gerais"`, `"grupo_vale"`, `"setor_principal"`).
- `uid`: O identificador único (`UID` NanoID ou caminho canônico como `"picos[0].mapas_gerais.conteudo"`) pré-alocado exclusivamente para esta parte na árvore Protobuf.
- `caminho_pdf`: Caminho do sub-PDF contendo apenas as páginas desta parte.
- `imagens`: Lista de caminhos relativos das imagens `.webp` extraídas para esta parte (ex: `["imagens/p4_i0.webp", "imagens/p4.webp"]`).

---

## 1. As Três Regras de Ouro de Isolamento e Atomicidade

> [!CAUTION]
> **1. Escopo Estrito por `UID` (`alvo=<uid_atribuido>`):**
> Você está rodando em paralelo com outros subagentes na mesma janela do Editor Aresta.
> - Passe **sempre** o `id_croqui` recebido em todas as chamadas MCP.
> - Opere **exclusivamente** sobre o `alvo` igual ao `uid` atribuído à sua parte.
> - **NUNCA** modifique setores, grupos ou botões de outras partes e **NUNCA** chame `aresta_salvar` ou `aresta_compilar` (isso é responsabilidade exclusiva da fase de compilação após todos os subagentes terminarem).
>
> **2. Proibição Absoluta de Edição Manual de Arquivos:**
> - É estritamente **PROIBIDO** criar ou editar arquivos `.md`, `croqui.yaml` ou `.json` no disco (`write_file`, `edit_file` ou scripts no terminal).
> - Toda leitura de esquema e toda gravação de dados DEVEM ser feitas pelas ferramentas MCP do `editor-aresta`.
>
> **3. Transação Atômica Única com `aresta_alterar_campo`:**
> - `aresta_alterar_campo` suporta a substituição declarativa completa de um objeto e de todas as suas listas `repeated` (`escaladas`, `mapas`, `referencias`, `participantes`, etc.) em **uma única chamada atômica** (`campos: dict`), preservando `uid`s informados e gerando NanoIDs automaticamente para novos itens.
> - Inspecione o PDF e as imagens primeiro, monte o payload completo da sua parte e envie tudo em uma única chamada `aresta_alterar_campo(alvo=uid, campos={...}, id_croqui=id_croqui)`.

---

## 2. Como Transcrever Cada Tipo de Parte

Primeiro, leia visualmente o sub-PDF da sua parte (`caminho_pdf`) e as imagens listadas em `imagens` usando `view_file` / `read_file`. Se tiver qualquer dúvida sobre nomes de campos ou valores de `Enum`, consulte `aresta_obter_esquema_proto(tipo_mensagem="Setor")` (ou `"Escalada"`, `"GrauVia"`, `"GrauBoulder"`, `"Grupo"`, `"ColecaoDeMapas"`).

### 2.1. Capa (`nome_parte == "capa"`)
Atualize os metadados gerais na raiz do `Croqui` / `Pico` (`alvo="picos[0]"` ou `alvo=uid` da raiz conforme o campo):
- No `Croqui` (`alvo=""` ou `uid` raiz): `caminho_thumbnail` (escolha a imagem representativa da capa em `imagens/...`).
- No `Pico` (`alvo="picos[0]"`): `nome`, `introducao` (se houver texto de apresentação na capa).

### 2.2. Seções Textuais / Apêndices (`Botao` com `pagina_markdown`)
Para partes textuais que não são setores nem grupos (`introducao`, `historia`, `hospedagem`, `regras_de_visitacao`, etc.), o `uid` recebido aponta para o `Botao` na raiz do croqui:
- Transcreva **100% do conteúdo textual** presente nas páginas do sub-PDF para o campo `pagina_markdown` (e ajuste o rótulo do botão no campo `texto`, ex: `"Introdução"`, `"História"`). Não resuma nem omita nenhuma informação.
- Se a página contiver imagens contextuais/ilustrativas em `imagens`, inclua-as no Markdown usando `![Legenda da imagem](imagens/pX_iY.webp)` (ou use `aresta_inserir_imagem_markdown`).
- Garanta sempre uma linha em branco antes e depois de cada tag de imagem no Markdown.
- Exemplo de chamada atômica:
  ```json
  {
    "alvo": "<uid_botao>",
    "id_croqui": "<id_croqui>",
    "campos": {
      "texto": "História e Acesso",
      "pagina_markdown": "Texto integral transcrito do PDF...\n\n![Vista da entrada](imagens/p2_i0.webp)\n\nContinuação do texto..."
    }
  }
  ```

### 2.3. Grupos (`nome_parte` começando com `grupo_` sem `_setor_`)
O `uid` recebido aponta para a mensagem `Grupo`:
- **`nome`**: Preencha com o nome próprio do grupo (ex: `"Vale Oculto"`). Não adicione o prefixo `"Grupo "` a menos que faça parte do nome original no PDF.
- **`introducao`**: Texto descritivo do grupo em Markdown. **NUNCA** inclua cabeçalhos H1 (`# Grupo ...`) no início do Markdown.
- **`mapas`**: Caso o grupo possua mapas de localização dos sub-setores, envie a lista `mapas: [{"caminho_imagem_mapa": "imagens/pX_iY.webp"}]`.
- **Sub-setores (`setores`)**: Não sobrescreva a lista `setores` do `Grupo` na chamada do grupo, pois `aresta_particionar_pdf_croqui` já pré-alocou os sub-setores dentro de `grupo.setores` com seus próprios `UID`s para serem preenchidos pelos subagentes dedicados a cada `grupo_X_setor_Y`.

### 2.4. Mapas Gerais (`nome_parte == "mapas_gerais"`)
O `alvo` recebido (`"picos[0].mapas_gerais.conteudo"`) aponta para a `ColecaoDeMapas` do pico:
- Inspecione as imagens da parte e selecione aquelas que representam mapas gerais/aéreos do pico.
- Envie a lista `mapas` em `aresta_alterar_campo`:
  ```json
  {
    "alvo": "picos[0].mapas_gerais.conteudo",
    "id_croqui": "<id_croqui>",
    "campos": {
      "mapas": [
        {
          "caminho_imagem_mapa": "imagens/p8_i0.webp"
        }
      ]
    }
  }
  ```

### 2.5. Setores e Sub-setores (`setor_...` ou `grupo_..._setor_...`)
O `uid` recebido aponta diretamente para a mensagem `Setor`:
- **Prefixação Obrigatória em `nome`**:
  - Para setores de vias: use **SEMPRE** o prefixo `"Setor "` (ex: `"Setor Bem-vindo"`).
  - Para blocos de boulder: use **SEMPRE** o prefixo `"Bloco "` (ex: `"Bloco 45º"`).
- **Proibição de H1 em `introducao`**:
  - **NUNCA** adicione títulos H1 (`# Setor ...` ou `# Bloco ...`) no campo `introducao`. O aplicativo já renderiza o título automaticamente a partir de `nome`. Subtítulos (`## Acesso`, `## Observações`) são permitidos quando houver texto descritivo. Se não houver texto geral do setor além das vias, deixe `introducao: ""`.
- **Lista de Escaladas (`escaladas`)**:
  Cada item da lista `escaladas` contém a variante `oneof tipo` (`via_esportiva`, `boulder`, `via_movel` ou `via_multiplas_enfiadas`) e opcionalmente `mapas` (quando houver foto/croqui exclusivo daquela escalada individual):
  - **Dificuldade (`GrauVia` / `GrauBoulder`)**:
    Use os nomes exatos do `Enum` em `croqui.proto` (ex: `"BR_7A"`, `"BR_5SUP"`, `"V7"`).
    Aplique obrigatoriamente os mapeamentos especiais da graduação brasileira:
    - `6c` → `"BR_6SUP"`
    - `6b` → `"BR_6_BARRA_6SUP"`
    - `6a` → `"BR_6"`
    - `5c` → `"BR_5SUP"`
    - `5b` → `"BR_5_BARRA_5SUP"`
    - `5a` → `"BR_5"`
    - Graus intermediários com barra (ex: `7b/c` ou `V7/8`) → `"BR_7B_BARRA_7C"`, `"V7_BARRA_V8"`.
  - **Proteções**: Converta notações como `"4+2"` em `quantidade_protecoes_intermediarias: 4` e `quantidade_protecoes_parada: 2`.
  - **Destaque**: Escaladas marcadas com estrela ou diamante recebem `"destaque": true`.
  - **Conquistadores / Participantes**: Preencha em `participantes` / `conquistadores` conforme o esquema Protobuf consultado em `aresta_obter_esquema_proto(tipo_mensagem="ViaEsportiva")`.
  - **Mapas Exclusivos de uma Escalada (`escaladas[].mapas`)**: Close-ups de agarras, saídas sentadas (*sit-start*) ou topos verticais exclusivos de uma única via/boulder vão dentro do item daquela escalada em `mapas: [{"caminho_imagem_mapa": "imagens/..."}]`.
- **Mapas Gerais do Setor (`mapas` na raiz do `Setor`)**:
  - Escolha as imagens em `imagens` que mostram a parede/bloco com as linhas e números das vias.
  - **Integridade da Imagem (`pX.webp` vs `pX_iY.webp`)**: Se a página do PDF possuía traçados vetoriais fatiados em mosaico, `aresta_particionar_pdf_croqui` terá gerado a imagem de página inteira `imagens/pX.webp` — prefira `pX.webp` sempre que as imagens individuais `pX_iY.webp` forem pedaços/fatias incompletas da parede.
  - Não repita imagens que são mapas dentro do campo Markdown `introducao`.

### Exemplo Completo de Chamada Atômica para um `Setor`
```json
{
  "alvo": "<uid_setor>",
  "id_croqui": "<id_croqui>",
  "campos": {
    "nome": "Setor Vila da Perdição",
    "introducao": "## Acesso\nTrilha de 10 minutos a partir do estacionamento principal.",
    "escaladas": [
      {
        "via_esportiva": {
          "nome": "Fenda do Medo",
          "dificuldade": "BR_7A",
          "quantidade_protecoes_intermediarias": 6,
          "quantidade_protecoes_parada": 2,
          "destaque": true,
          "descricao": "Início técnico em regletes seguido de diedro."
        },
        "mapas": [
          {
            "caminho_imagem_mapa": "imagens/p11_i2.webp"
          }
        ]
      },
      {
        "via_esportiva": {
          "nome": "Diedro Oculto",
          "dificuldade": "BR_6SUP",
          "quantidade_protecoes_intermediarias": 5,
          "quantidade_protecoes_parada": 2
        }
      }
    ],
    "mapas": [
      {
        "caminho_imagem_mapa": "imagens/p11.webp"
      }
    ]
  }
}
```

---

## 3. Preservação Estrita de `UID`s ao Atualizar Croqui Existente

Quando você estiver atualizando uma parte de um croqui que já possuía dados:
1. Antes de montar sua alteração, chame `aresta_obter_arvore(alvo=uid, id_croqui=id_croqui)` para ler o estado atual daquela entidade.
2. Se o PDF antigo e o PDF novo daquela parte forem equivalentes sem nenhuma alteração de conteúdo, não chame `aresta_alterar_campo` e retorne `"Nenhuma mudança necessária"`.
3. Caso haja mudanças, **PRESERVE RIGOROSAMENTE** todos os campos `uid`, `alvo_uid` e `pontos_uids` das escaladas, mapas, pontos de interesse e referências que continuam existindo, incluindo-os nos dicionários enviados na lista para `aresta_alterar_campo`.
4. Para novas escaladas ou novos mapas adicionados na nova edição, basta omitir o campo `uid` no dicionário do item novo (o Editor gerará um novo NanoID automaticamente).

---

## 4. Conferência e Auto-Validação Final

Após executar `aresta_alterar_campo`:
1. Chame `aresta_obter_arvore(alvo=uid, id_croqui=id_croqui)` para verificar a subárvore gravada em memória.
2. Confirme que todas as escaladas do PDF estão presentes, que os `UID`s foram gerados/preservados e que os caminhos das imagens (`imagens/...`) estão corretos.
3. Retorne ao Agente Orquestrador um resumo conciso com o `uid` atualizado, total de escaladas e mapas registrados.

## Quando usar essa habilidade

Use essa habilidade quando precisar transcrever ou atualizar uma parte específica de um croqui PDF diretamente na árvore Protobuf do Editor Aresta via MCP.
