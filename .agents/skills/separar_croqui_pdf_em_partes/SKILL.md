---
name: separar_croqui_pdf_em_partes
description: Separa um croqui em partes lógicas para processamento posterior.
---

# Separar PDF de Croqui de Escalada em Partes

Um PDF de croqui de escalada é composto por várias partes. Como parte de um workflow para extrair
as informações do croqui, separar o PDF em partes lógicas é um passo importante.

## Partes de interesse

Dentre as partes do PDF, há várias que são de interesse para o workflow:
- **capa**: capa do croqui
- **secoes_textuais**: Seções textuais como disclaimer, introdução, história, regras de visitação, hospedagem, etc que não estão incluídas nas seções a serem ignoradas abaixo. Cada seção textual deve ter uma parte separada no arquivo .json.
- **mapas_gerais**: Mapas gerais do pico de escalada, incluindo vista aérea
- **setores**: Descrição de cada setor, com vias ou boulders, trilhas, acesso, etc. Cada setor deve ter uma parte separada no arquivo .json começando com o prefixo "setor_".

Além disso, provavelmente haverão várias partes que não são úteis para o workflow, as quais devem ser totalmente ignoradas e não adicionadas ao mapa de partes. Essas partes a serem ignoradas, são, estritamente:
- Qualquer índice de páginas do PDF
- Qualquer índice de vias ou boulders descritos anteriormente e re-ordenados (por exemplo, índice de todas as vias por grau de dificuldade, ou por ordem alfabética, etc)


## Como separar o PDF

### 1. Criação Resiliente da Pasta do Croqui

Antes de separar as páginas, você precisa identificar as informações exatas sobre a localização do croqui:
- País
- Estado
- Cidade
- Nome do Pico de Escalada

**Estratégia de Busca (Siga estritamente a ordem):**
1. **Capa e Introdução:** Inspecione visualmente as primeiras páginas do PDF para extrair esses dados.
2. **Resto do PDF:** Se faltar alguma informação (por exemplo, a cidade ou estado), inspecione o restante do PDF lendo outras páginas.
3. **Busca na Internet:** Se mesmo após vasculhar o PDF você não encontrar todas as informações geográficas, utilize a ferramenta de `search_web` na internet para pesquisar onde fica o pico de escalada e deduzir a cidade, estado e país corretos.
4. **Último Recurso:** Apenas se não encontrar de forma alguma após a busca exaustiva na web, utilize `desconhecido` para o campo faltante. Não invente ou alucine dados geográficos.

Com essas informações completas e validadas, crie a pasta para o croqui dentro da pasta `database` seguindo rigorosamente o formato: `database/<pais>_<estado>_<cidade>_<pico_de_escalada>`.
- Use apenas letras minúsculas.
- Remova todos os acentos.
- Substitua espaços por `_` (underscores).

> [!WARNING]
> A correta formatação do arquivo `partes.json` que você irá criar na etapa 2 é fundamental. Erros de sintaxe ou vírgulas sobrando impedirão o andamento de toda a arquitetura. Revise cuidadosamente o JSON resultante.

**MUITO IMPORTANTE:** Ao finalizar seu trabalho, você **DEVE** retornar na sua mensagem final o caminho exato da pasta que você criou, para que o agente orquestrador saiba onde continuar o fluxo.

### 2. Separação em Partes

Leia todas as páginas do PDF, identificando o conteúdo de cada uma, e construa um mapa de parte de
interesse para páginas que compõem essa parte baseado nas partes de interesse e não interesse mencionadas acima.
Esse mapa deve ser um arquivo `partes.json` dentro da pasta que você acabou de criar. Ele deve ter uma estrutura como a seguinte:

```json
{
    "capa": [0],
    "introducao": [1],
    "historia": [4],
    "outras_atracoes": [5, 6, 7],
    "mapas_gerais": [8, 9],
    "setor_vila_da_perdicao": [11],
    "setor_casa_de_escalada": [12, 13],
    "setor_bebedouro_da_onca": [14],
    "setor_savassinha": [15, 16],
}
```

Lembrando que:
> [!WARNING]
> **A contagem de páginas DEVE OBRIGATORIAMENTE começar em 0**. Não use 1-index (primeira página é 0).
- As chaves (Keys) no JSON devem ser escritas sempre sem acentos e usando `_` (underscore) para separar palavras.
- O valor de cada `key` deve ser um tipo `array` de números inteiros representando os números reais das páginas.
- `secoes_textuais` e `setores` são objetos que mapeiam cada seção/setor para um array de inteiros representando os números das páginas.
- Se uma parte não existir na imagem, **NÃO CRIAR** chave vazia. Ela deve ser estritamente omitida do JSON.

## Croquis de boulder

Croquis de boulders usualmente são organizados em blocos, onde vários blocos juntos agrupam-se em um "setor". Na conversão para um arquivo `partes.json` considere as seguintes regras:
- Cada bloco independente deve ser representado como um setor, ou seja, `setor_X.md`.
- O "setor" que agrupa os blocos deve ser representado como um grupo de setores, ou seja, `grupo_X.md`.
- Cada bloco dentro do grupo deve ser representado como um setor dentro do grupo, ou seja, `grupo_X_setor_Y.md`.

Desse modo, os boulders individuais poderão ser representados apropriadamente na nossa database.

## Grupos de setores 

É possível que hajam grupos de setores no croqui, às vezes também chamados de setores com sub-setores.
Nesse caso, arquivo do grupo passa a ser `grupo_X.md`, e cada subsetor fica em um arquivo `grupo_X_setor_Y.md`, ou seja, `grupo_X`, seguido por um underline (`_`), e então informações sobre cada sub-setor (`setor_Y.md`). Exemplo:

```json
{
    "capa": [0],
    "introducao": [1],
    "mapas_gerais": [2, 3],
    "grupo_vila_araucaria": [4, 5],
    "grupo_vila_araucaria_setor_savassinha": [6, 7],
    "grupo_vila_araucaria_setor_fornalha": [8],
}
```

Grupos (Setores com sub-setores) são representados em `croqui.proto` utilizando o proto de Grupo, que possui sub protos de `setores`. No `croqui.yaml`, a mensagem `Pico` pode listar ou setores ou grupos. Utilize dessa habilidade para listar grupos.

## Quando usar essa habilidade

Use essa habilidade quando precisar separar um croqui em partes lógicas para processamento posterior.
