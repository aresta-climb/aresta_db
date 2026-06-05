---
description: Como preparar um croqui em PDF para ser convertido para dado estruturado
---

Essa workflow detalha o processos de extrair informação de preparação de croquis de escalada em formato PDF para que possam ser convertidos para o formato estruturado em Markdown com YAML Frontmatter, com o YAML seguindo o formato do protocol buffer `aresta_api/proto/croqui.proto`.

Para iniciar esse workflow, você receberá um arquivo PDF para fazer a conversão para dados estruturados de acordo com o modelo definido em `aresta_api/proto/croqui.proto`. 

> [!IMPORTANT] 
> **Ação Autônoma:** Você **NÃO DEVE** pedir permissão ao usuário entre as etapas deste workflow. Siga o plano agressivamente, executando as etapas de forma contínua até o último passo ou até encontrar um erro terminal irrecuperável.

### 1. Inspecione o PDF e crie a pasta da conversão, o arquivo `partes.json` e a pasta `raw_pdf_contents`

1. Tente ver o conteúdo textual do PDF usando o pymupdf. Caso o conteúdo textual já for o suficiente para entender o conteúdo, trabalhe apenas com ele. Caso não for possível, abra o PDF diretamente usando o comando `view_file` e inspecione o PDF visualmente. Utilize esse entendimento para realizar duas tarefas:

  a) Crie a pasta onde vai ser localizado o PDF convertido. O nome da pasta deve seguir o formato `<pais>_<estado>_<cidade>_<pico_de_escalada>`, com os nomes sem acentos e usando `_` (underscores) para separar palavras. A pasta deve ser localizada dentro da pasta `database` (i.e. `database/<pasta_do_pdf_convertido>`). Se por acaso a pasta já existir, crie uma nova com um sufixo (2, 3, etc). NOTA: caso essa pasta já existir, e já tiver um arquivo `partes.json`, pode finalizar o processamento desse PDF aqui e pular para o passo 2 (resumo e walkthrough para o usuário).

  b) Gere o arquivo `partes.json` dentro da pasta criada. Para isso, utilize a skill @separar_croqui_pdf_em_partes com o input da inspeção do PDF.

2. Copie o arquivo pdf para a pasta `database/<pasta_do_pdf_convertido>/raw_original_pdf`, e salve o arquivo com o nome `croqui_original.pdf`.

3. Execute o comando `python scripts/repartir_pdf.py database/<pasta_do_pdf_convertido>` para gerar a pasta `raw_pdf_contents`.

### 2. Resumo e walkthrough para o usuário

Volte agora para o usuário com um walkthrough do trabalho que foi feito, pedindo para o usuário, e passando as seguintes instruções para eles:
1. Conferir o arquivo `partes.json` gerado. Caso forem necessárias modificações, executar `python scripts/repartir_pdf.py database/<pasta_do_pdf_convertido>`
2. Conferir as imagens na pasta `raw_pdf_contents/imagens` se possuem todo o conteúdo do PDF. Caso for necessário também extrair fotos das páginas inteiras dos PDFs, executar `python scripts/repartir_pdfs.py database/<pasta_do_pdf_convertido> --incluir_paginas`. Caso o sistema inteligente de agrupamento de imagens estiver fazendo bobagem, use `python scripts/repartir_pdfs.py database/<pasta_do_pdf_convertido> --apenas-extrair`.
3. Após essas conferências, siga em frente usando o workflow `/converter_pdf_para_croqui database/<pasta_do_pdf_convertido>`