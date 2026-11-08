---
name: separar_croqui_pdf_em_partes
description: Separa um croqui em partes lógicas e inicializa os esqueletos na árvore Protobuf via MCP para processamento posterior.
---

# Separar PDF de Croqui de Escalada em Partes (100% via MCP)

Um PDF de croqui de escalada é composto por várias partes lógicas. Nesta skill, você inspecionará visualmente o PDF, garantirá que o croqui esteja aberto ou criado no **Editor Aresta** via MCP e executará o particionamento automatizado com pré-alocação de `UID`s na árvore Protobuf (`aresta_particionar_pdf_croqui`).

> [!CAUTION]
> **Proibição Estrita de Manipulação Manual de Arquivos e Scripts Ad-Hoc:**
> - **NUNCA** crie pastas manualmente em `database/`, nem escreva arquivos `partes.json`, `.md` ou `croqui.yaml` usando ferramentas de escrita em disco (`write_file`, `edit_file` ou comandos de terminal).
> - **NUNCA** crie ou execute scripts Python no terminal para extrair texto ou fatiar páginas do PDF.
> - Toda abertura/criação do croqui e todo o particionamento do PDF DEVEM ocorrer exclusivamente através das ferramentas MCP do `editor-aresta`.

---

## 1. Partes de Interesse vs. Partes Ignoradas

Dentre as páginas do PDF, mapeie apenas as partes úteis para o croqui:
- **`capa`**: Capa do croqui (dados gerais do pico, foto de capa, créditos/autores).
- **Seções textuais (apêndices)**: Seções informativas como `introducao`, `disclaimer`, `historia`, `regras_de_visitacao`, `hospedagem`, `como_chegar`, ` ética`, etc. Cada seção textual independente deve ter sua própria chave no dicionário `partes` (ex: `"introducao": [1]`, `"historia": [2, 3]`).
- **`mapas_gerais`**: Mapas gerais do pico de escalada, incluindo vista aérea, mapa de trilhas e localização dos setores.
- **`setor_<slug>`**: Descrição de cada setor ou bloco independente, contendo vias ou boulders, fotos de parede, trilhas e acesso. Cada setor deve usar o prefixo `"setor_"` (ex: `"setor_vila_da_perdicao": [11]`).
- **`grupo_<slug>` e `grupo_<slug>_setor_<sub_slug>`**: Quando o croqui possui grupos de setores (ou setores divididos em sub-setores / conjuntos de blocos de boulder).

### Partes que DEVEM ser estritamente ignoradas (omitidas):
- Qualquer sumário ou índice de páginas do PDF.
- Qualquer índice remissivo de vias ou boulders já descritos nos setores e apenas reordenados (por exemplo: índice de todas as vias por grau de dificuldade ou por ordem alfabética).
- Caso uma parte não exista no PDF, **jamais crie chave com lista vazia** (`[]`). Omita a chave completamente.

---

## 2. Leitura Visual do PDF e Identificação Geográfica

> [!IMPORTANT]
> **Leitura Visual Direta com `view_file` / `read_file`:**
> Inspecione o arquivo `.pdf` diretamente usando a ferramenta nativa de leitura de arquivos (`view_file` / `read_file`), que suporta PDFs de forma multimodal.

Antes de criar ou abrir o croqui no Editor Aresta, identifique os metadados geográficos exatos:
- **País** (código ISO de 2 letras em minúsculas, ex: `"br"`)
- **Estado** (sigla de 2 letras, ex: `"mg"`, `"rj"`, `"sp"`)
- **Cidade** (ex: `"Ouro Preto"`, `"Cocalzinho de Goiás"`)
- **Nome do Pico de Escalada** (ex: `"Ouroboulder"`, `"Cocalzinho"`)

**Estratégia de Busca (Siga estritamente a ordem):**
1. **Capa e Introdução:** Inspecione visualmente as primeiras páginas do PDF para extrair esses dados.
2. **Restante do PDF:** Se faltar alguma informação (como cidade ou estado), inspecione outras páginas de texto ou mapas de acesso.
3. **Busca na Internet (`search_web`):** Se o PDF não informar explicitamente a cidade ou o estado do pico, pesquise na web onde fica o pico de escalada para obter a localização real.
4. **Último Recurso:** Apenas se não for possível encontrar mesmo após busca na web, utilize `"desconhecido"` para o campo faltante. Não invente dados geográficos.

---

## 3. Regras para Croquis de Boulder e Grupos de Setores

### 3.1. Croquis de Boulder
Croquis de boulders costumam organizar vários blocos dentro de áreas/setores maiores:
- Cada bloco independente sem agrupamento superior deve ser mapeado como `"setor_<nome_do_bloco>"`.
- Uma área/setor que agrupa vários blocos deve ser mapeada como `"grupo_<nome_do_grupo>"`.
- Cada bloco pertencente àquele grupo deve ser mapeado como `"grupo_<nome_do_grupo>_setor_<nome_do_bloco>"`.

> [!IMPORTANT]
> **Páginas com Fotos Gerais e Fotos de Detalhe de Escaladas:**
> Se uma ou mais páginas consecutivas de um bloco ou setor contiverem tanto a visão geral da pedra quanto fotos de close-up/detalhes de boulders ou vias específicas (ex: saídas sentadas, pegas-chave ou agarras), **todas essas páginas devem ser agrupadas na mesma chave de setor**.
> **NUNCA crie chaves separadas para fotos de escaladas individuais**. O subagente conversor vinculará fotos de detalhe diretamente dentro de `escaladas[].mapas` naquele setor.

### 3.2. Formato do Dicionário `partes`
- **Contagem de páginas 0-indexed obrigatória**: A primeira página do PDF é sempre `0` (nunca use 1-index).
- As chaves devem conter apenas letras minúsculas, números e `_` (sem acentos, espaços ou caracteres especiais).
- Exemplo de dicionário `partes`:
  ```json
  {
    "capa": [0],
    "introducao": [1],
    "historia": [4],
    "mapas_gerais": [8, 9],
    "grupo_vila_araucaria": [10],
    "grupo_vila_araucaria_setor_savassinha": [11, 12],
    "setor_vila_da_perdicao": [13],
    "setor_casa_de_escalada": [14, 15]
  }
  ```

---

## 4. Execução via Ferramentas MCP do Editor Aresta

Com os dados geográficos e o dicionário `partes` prontos, execute a sequência abaixo no servidor MCP (`editor-aresta`):

### Passo 1: Consultar Croquis Disponíveis (`aresta_listar_croquis`)
Chame `aresta_listar_croquis(busca="<nome_pico>")` para verificar:
- `abertos`: croquis que já estão abertos em janelas ativas do Editor Aresta.
- `em_andamento`: rascunhos locais que já foram iniciados anteriormente.
- `oficiais`: croquis oficiais publicados no repositório de produção.

### Passo 2: Abrir, Importar ou Criar o Croqui
Escolha a ferramenta adequada conforme o caso:
1. **Croqui já aberto na sessão**: Se já estiver listado em `abertos`, anote seu `id_croqui`.
2. **Continuar rascunho existente ou pasta local**: Chame `aresta_abrir_croqui_existente(identificador="<id_ou_pasta>")`.
3. **Atualizar um croqui oficial de produção**: Chame `aresta_importar_croqui_oficial(id_oficial="<id_oficial>")`.
4. **Criar um novo croqui do zero**: Chame `aresta_criar_novo_croqui(nome_pico="...", cidade="...", estado="...", pais="br")`.

> [!NOTE]
> O Editor Aresta suporta múltiplas janelas abertas simultaneamente (uma por `id_croqui`). Sempre registre o `id_croqui` retornado pela ferramenta de abertura/criação e repasse-o nas chamadas seguintes.

### Passo 3: Particionar o PDF e Pré-Alocar Esqueletos (`aresta_particionar_pdf_croqui`)
Chame `aresta_particionar_pdf_croqui`:
```json
{
  "caminho_pdf": "C:/caminho/absoluto/para/arquivo.pdf",
  "partes": {
    "capa": [0],
    "introducao": [1],
    "mapas_gerais": [2, 3],
    "setor_principal": [4, 5]
  },
  "id_croqui": "<id_croqui>"
}
```
Esta ferramenta executa automaticamente em uma única operação atômica:
1. Fatia o PDF em sub-PDFs por parte e extrai todas as imagens `.webp` para a pasta `imagens/` do croqui (detectando automaticamente páginas fatiadas em mosaico e renderizando a página inteira `pX.webp` em alta resolução quando necessário).
2. Extrai os candidatos vetoriais de texto e desenho via `PyMuPDF` (`*_dados.json`).
3. Pré-aloca na árvore Protobuf em memória os esqueletos de `Botao` (apêndices), `ColecaoDeMapas` (`mapas_gerais`), `Grupo` e `Setor`, atribuindo e preservando os `UID`s NanoID de cada entidade.
4. Retorna o mapa completo `partes` contendo para cada chave: `uid`, `tipo`, `caminho_pdf`, `imagens` e `dados_vetoriais`.

### Passo 4: Retorno Obrigatório para o Orquestrador
Ao finalizar, retorne em sua resposta final de forma estruturada:
- `id_croqui`: O identificador do croqui aberto no Editor Aresta.
- `caminho_database`: O caminho da pasta de trabalho do croqui.
- `partes`: O dicionário retornado por `aresta_particionar_pdf_croqui` contendo o `uid`, `tipo`, `caminho_pdf` e lista de `imagens` de cada parte, permitindo que o Agente Orquestrador dispare os subagentes conversores em paralelo isolados por `uid`.

## Quando usar essa habilidade

Use essa habilidade sempre que precisar inspecionar um PDF de croqui de escalada, inicializar ou abrir o croqui correspondente no Editor Aresta e particioná-lo em partes lógicas com `UID`s pré-alocados via MCP.
