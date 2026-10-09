# Spec Delta

## MODIFIED Requirements

### Requirement: Biblioteca de Regras de Imagens Markdown (Library-First)
O sistema SHALL fornecer uma biblioteca autossuficiente (`editor.core.imagens_markdown`) para regras de negócio de nomenclatura, sanitização, formatação de tags e processamento de imagens destinadas ao Markdown.
- **Sanitização de Nomes e Limite de Comprimento**: A biblioteca SHALL converter nomes brutos para formato `snake_case`, em caracteres minúsculos, sem acentos ou símbolos especiais, com extensão `.webp`, truncando o tronco (*stem*) em no máximo 40 caracteres para prevenir estouros de caminho no sistema operacional.
- **Prevenção de Colisões**: Ao sugerir um nome para uma pasta de destino, a biblioteca SHALL verificar a existência de arquivos com o mesmo nome e adicionar sufixos numéricos sequenciais (`_1`, `_2`).
- **Nomenclatura de Capturas de Tela**: Para imagens provenientes da área de transferência, a biblioteca SHALL gerar nomes no formato `imagem_AAAAMMDD_HHMMSS.webp`.
- **Formatação de Tag**: A biblioteca SHALL gerar strings no formato `![<legenda>](imagens/<nome_arquivo>)`.
- **Compressão e Persistência**: A biblioteca SHALL aplicar a conversão de imagem em formato WebP com qualidade lossy 85 e limite de área de 4.194.304 pixels (`comprimir_imagem_para_bytes_webp`) antes de gravar no disco.

#### Scenario: Sanitização de Nome de Arquivo
- **WHEN** a função de sanitização recebe a string `"Foto do Setor Principal (Cópia).png"`
- **THEN** ela SHALL retornar `"foto_do_setor_principal_copia.webp"`.

#### Scenario: Truncamento de Nome Muito Longo
- **WHEN** a função de sanitização recebe um nome com tronco superior a 40 caracteres
- **THEN** ela SHALL truncar o tronco em 40 caracteres, remover sublinhados residuais no final e anexar a extensão `.webp`.

#### Scenario: Incremento Numérico em Caso de Colisão
- **WHEN** a função de geração de nome padrão recebe um nome cujo arquivo já existe na pasta de destino
- **THEN** ela SHALL retornar o nome acrescido de um sufixo numérico que garanta a unicidade do novo arquivo.

#### Scenario: Formatação de Tag com e sem Legenda
- **WHEN** a função de formatação de tag recebe o arquivo `"setor_bloco.webp"` com a legenda `"Bloco Central"`
- **THEN** ela SHALL retornar `"![Bloco Central](imagens/setor_bloco.webp)"`.
- **WHEN** a função de formatação de tag recebe o arquivo `"setor_bloco.webp"` com a legenda vazia
- **THEN** ela SHALL retornar `"![](imagens/setor_bloco.webp)"`.
