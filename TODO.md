# TODO

Tarefas ainda a fazer na database.

## Croquis precisando consertar os pontos nos mapas

1. br_mg_conceicao_do_mato_dentro_festboulder: por exemplo no setor colina temos
   vários boulders com o mesmo nome mas números diferentes. Talvez tenha que
   re-extrair os números desse croqui. Igual ao problema do ouroboulder.
2. Muitos croquis precisando renomear de 8 e 9 pra 08 e 09!

## Editor

- Continuar a partir da migração do editor de mapas, na conversa de aresta_db:
  "Migrating Editor Mapas MVC"
- Muitas melhorias para undo/redo:
  - No editor de mapas, adicionar novos pontos ou remover pontos não está como
    parte do ctrl+z

## Inspeções

- Inspecionar se tem que converter quadrados para círculos
- Inspecionar se tem como extrair desenhos dos mapas para refazer a parte das
  extrações de imagens/mapas com maior qualidade.
- Adicionar linter (warning) caso o croqui contenha POIs órfãos (sem referência
  apontando para eles).

## Geral

- Criar um novo 'partes.proto' e converter todos os partes.json para partes.yaml
  seguindo esse formato, e atualizar as skills para seguir esse novo proto.
- Coloque um script que duplica imagens caso estiverem sendo usadas em mais de
  um local no mesmo arquivo .md. E coloque instruções para o modelo referenciar
  a mesma imagem mais de uma vez caso houverem sub-imagens na imagem.
- OCR/map recognition para mapas gerais também.
- Suportar boulders que tem marcado início e fim (por exemplo 2E no
  ouroboulder).
- Implementar algum tipo de desambiguação entre id_no_mapa das escaladas e os
  ids realmente disponíveis no mapa, e ter algum tipo de métrica de saúde sobre
  isso.
- Corrigir o partes.json para ser um partes.yaml baseado em um partes.proto, e
  trocar todos para pararem de ser JSON.

## Cambotas

Precisa de MUITO trabalho no croqui de Cambotas pra fazer sentido dele.

# Bocaina boulder

- 1 Pressão Enrustida - Qual é qual? Eita setor confuso.
- 4 Canil - qual é o 5. ZAC?
- 6 Cabelin - qual é o 14. La Qualitê?
- 11 Bloco 45o - falta do 19 ao 23.
- 12 Essência - falta 8 Escravos de chó
- Tem outros mapas que mereceriam marcar os finais pra conseguir ficar fácil de
  ver vários boulders

# Salão encantado

- Fazer o primeiro mapa geral ser na verdade como chegar, e manter só o 2o.

# Sinuosa

- Fazer os primeiros 2 mapas gerais serem como chegar, e manter só o 3o mapa.

# Vó gusta

- Mapas gerais são como chegar, não mapas gerais

# Pedra da divisa

- Mapas gerais são como chegar, não mapas gerais

# Diamaboulder

- Primeiro mapa geral é como chegar, não mapas gerais

# TODOs do Linter

- Adicionar verificação de Linter para emitir warnings caso o
  `indice_mapa_padrao` de um Setor, Grupo ou Escalada estiver apontando para um
  índice de mapa inválido (fora dos limites da lista de mapas).
- Adicionar verificação de Linter para emitir warnings caso o
  `indice_mapa_padrao` de uma Escalada apontar para um mapa onde a escalada não
  possui referência (`Referencia` na lista de referencias do mapa).
- Adicionar verificação de Linter para emitir warnings caso um Ponto de
  Interesse (POI) em um mapa não for referenciado por nenhuma `Referencia`
  naquele mesmo mapa (pois eles não serão desenhados no app frontend). Publicar
  ouroboulder
