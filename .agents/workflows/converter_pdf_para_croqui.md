---
description: Como converter um croqui em formato PDF em dado estruturado
---

Essa workflow detalha o processo de extrair informação de croquis de escalada em formato PDF e converter eles para o formato estruturado em Markdown com YAML Frontmatter, com o YAML seguindo o formato do protocol buffer `aresta_api/proto/croqui.proto`.

Para iniciar esse workflow, você receberá uma pasta dentro de `database` ou seja, `database/<croqui>/*`, que conterá um arquivo `partes.json`. Além disso, essa pasta também conterá o pdf já pré-processado de acordo com esse arquivo JSON em `raw_pdf_contents/*.pdf` e `raw_pdf_contents/imagens/*`. Se limite a esses paths durante a conversão.

Seu trabalho é fazer para fazer a conversão desse PDF pré-processado para dados estruturados de acordo com o modelo definido em `aresta_api/proto/croqui.proto`. 

> [!IMPORTANT] 
> **view_file**: visualize arquivos pdf **diretamente** usando o comando `view_file`. Você **não deve** abrir navegadores, acessar URL externa ou utilizar de outro meio para visualizar PDFs além da tool `view_file`.
> **Ação Autônoma:** Você **NÃO DEVE** pedir permissão ao usuário entre as etapas deste workflow. Siga o plano agressivamente, executando as etapas de forma contínua até o último passo ou até encontrar um erro terminal inrecuperável.


### 1. Inspecione o arquivo `partes.json`

Inspecione o arquivo `partes.json` para entender quais as partes do PDF que foram extraídas para você, e que devem ser convertidas para o formato de croqui.proto.

Dentro da pasta `raw_pdf_contents`, irão já existir um arquivo `.pdf` para cada item de `partes.json`, e uma pasta `imagens/<parte>` contendo todas as imagens dessa parte do PDF extraídas e comprimidas para o formato `.webp`. Esses arquivos serão necessários para a próxima fase. Ignore a pasta `raw_imagens` que também é gerada.

### 2. Converta cada parte individual do croqui para Markdown com Frontmatter YAML

Itere ativamente sobre cada parte especificada em `partes.json`.

// Parallel
Para cada arquivo correspondente a `<parte>.pdf` na pasta `raw_pdf_contents` leia o conteúdo do arquivo `database/<croqui>/raw_pdf_contents/<parte>.pdf` e ative/utilize a skill referenciada por `@converter_parte_croqui_para_markdown` para interpretar o arquivo PDF e fazer o output de um arquivo markdown com o conteúdo do PDF. Seu **Output final** dessa parte deve ser o arquivo `database/<croqui>/<parte>.md`.

### 3. Gere o arquivo final

Gere o arquivo final `croqui.yaml` que une todos os arquivos .md que foram gerados, listando todos eles no arquivo YAML. Para tanto, utilize a opção de `caminho` dos oneofs de arquivo (como descrito em `croqui.proto`) para apenas listar os arquivos `.md` no arquivo `croqui.yaml`, sem incluir o conteúdo desses arquivo diretamente.

Além disso, **defina obrigatoriamente** o campo `ultima_migracao` com o ID numérico da migração mais recente presente no diretório `migracoes/` (por exemplo, `1`).

Nesse arquivo, sempre preencha o `caminho_thumbnail` com a mesma imagem que está na `capa.md`, se houver. Alternativamente, escolha uma imagem representativa para o croqui.

Nesse arquivo, **nunca** adicione marcações sobre os campos `revisado_*`, pois isso é reservado para os humanos que vão verificar seu trabalho manualmente depois.

### 4. Prepare o croqui convertido para submissão

Execute `python scripts/deploy_generated.py` para corrigir os caminhos das imagens nos arquivos gerados e para gerar os arquivos `compilado.yaml` e `compilado.binarypb` a partir do arquivo `croqui.yaml` para confirmar que o formato de todos os arquivos está correto.

### 5. Revise os arquivos gerados

Revise os arquivos gerados para ter certeza que não há erros de parsing nos arquivos .md, incluindo a seção de Frontmatter YAML. Também tenha certeza que o nesting alinhe perfeitamente com `croqui.proto`. Também confirme que todas as seções no arquivo `partes.json` têm um arquivo `.md` equivalente gerado. Caso não tiver, retorne ao passo 3 com os arquivos faltando. Por fim, execute o script `python scripts/verificar_binarypb.py <arquivo_binarypb>` para confirmar que o arquivo gerado na etapa anterior não possui erros.

### 6. Volte ao usuário

Por fim, volte com o walkthrough para o usuário, e faça as seguintes instruções para ele:
1. Analizar o arquivo generated/<croqui>/compilado.md, comparando com o PDF original, e fazer quaisquer correções que forem necessárias.
2. Fazer correções nas imagens usando `python scripts/editar_imagens.py database/<croqui>` para que fiquem perfeitas para as próximas etapas.
3. Abrir os mapas do croqui usando `python scripts/editar_mapas.py database/<croqui>`. Caso o croqui já tiver os pontos de interesse extraídos, ajustá-los e trabalho completado! Pode submeter o croqui!
4. Caso tiverem pontos de interesse faltando, executar a workflow `/extrair_informacoes_dos_mapas database/<croqui>`.