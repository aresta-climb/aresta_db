## Purpose

Verifica e emite avisos durante o deploy sobre referências a imagens inexistentes em mapas, miniaturas e textos Markdown do croqui.

## ADDED Requirements

### Requirement: Validação de Imagens Ausentes durante o Deploy
O sistema SHALL verificar a existência no disco de todas as imagens locais referenciadas no croqui compilado, incluindo mapas, miniaturas e imagens incorporadas em textos Markdown.
- **Campos de Mapa e Croqui**: O validador SHALL inspecionar `caminho_imagem_mapa` e `caminho_thumbnail`.
- **Imagens em Markdown**: O validador SHALL extrair referências a imagens no formato `![...](caminho)` em todos os campos textuais (`descricao`, `conteudo`, etc.).
- **Ignorar Links Externos**: O validador SHALL ignorar URLs externas iniciadas por `http://` ou `https://`.
- **Emissão de Avisos (Não Bloqueante)**: Caso o arquivo de imagem não seja encontrado no disco em relação à pasta do croqui, o validador SHALL emitir um aviso no console informando o ID do croqui e o caminho da imagem ausente, sem interromper a compilação.

#### Scenario: Imagem local existente no disco
- **WHEN** o croqui referencia uma imagem em mapa ou Markdown e o arquivo correspondente existe na pasta do croqui
- **THEN** o sistema compila o croqui sem emitir avisos de imagem ausente.

#### Scenario: Imagem de mapa inexistente no disco
- **WHEN** o campo `caminho_imagem_mapa` referencia um caminho cujo arquivo não existe no diretório do croqui
- **THEN** o sistema emite um aviso no console indicando que a imagem do mapa não foi encontrada no disco e continua o processo de deploy.

#### Scenario: Imagem referenciada no Markdown inexistente no disco
- **WHEN** um texto Markdown contém a marcação `![Foto](imagens/inexistente.webp)` e o arquivo não existe no disco
- **THEN** o sistema emite um aviso no console identificando a referência quebrada e o ID do croqui.

#### Scenario: Referência a URL externa no Markdown
- **WHEN** um texto Markdown contém uma imagem apontando para URL externa com protocolo `http://` ou `https://`
- **THEN** o validador ignora a verificação no sistema de arquivos local e não emite aviso de ausência.
