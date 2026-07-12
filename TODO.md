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
- Adicionar linter (warning) caso `indice_mapa_padrao` estiver apontando para um
  mapa inválido ou para um mapa que não contenha a escalada referenciada.
- Adicionar linter (warning) caso o croqui contenha POIs órfãos (sem referência
  apontando para eles).

## MIGRAÇÃO DO ESQUEMA DE MAPAS

- Script para validar que os pontos de interesse todos encontram uma escalada
  para referenciar
- Por quê as imagens do 'acesso' do baú agora estão incluindo legenda?
- Atualizar a documentação do workflow e skill de extrair mapas.
- Extrair as mensagens de Mapa e sub-mensagens para um arquivo mapa.proto.
- Converter os arquivos .json das pastas de mapas para formato YAML seguindo o
  proto Mapa.
- Atualizar todas as pastas raw_maps para estar de acordo com os novos formatos

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

## Igarameca

- Criar um super-setor pedra grande pra o mapa geral do complexo pedra grande

## Cambotas

Precisa de MUITO trabalho no croqui de Cambotas pra fazer sentido dele.

## Bombonera

Tem um 8-9 no mapa que temos que ver o que fazer para mapear para a via.

## Ouroboulder

- A imagem que está como primeira imagem do bloco Mantra no setor Bonsai na
  verdade é o bloco Prodígio, que não está marcado no mapa.
  - grupo_bonsai_setor_bloco_mantra_p1.webp
  - grupo_bonsai_setor_bloco_seg_samambaia_p0.webp
  - grupo_mont_blanc_setor_bloco_o_pequeno_p0.webp
  - grupo_pedreira_setor_bloco_complexo_p3.webp
  - grupo_pedreira_setor_bloco_deep_inside_p1.webp
  - grupo_pedreira_setor_bloco_entretidos_p3.webp
  - grupo_pedreira_setor_bloco_fiat_lux_p0.webp
  - grupo_pedreira_setor_bloco_hora_da_janta_p0.webp
  - grupo_pedreira_setor_bloco_jah_p0.webp
  - grupo_pedreira_setor_bloco_joao_de_barro_p0.webp
  - grupo_pedreira_setor_bloco_joao_de_barro_p1.webp
  - grupo_pedreira_setor_bloco_joao_de_barro_p2.webp
  - grupo_pedreira_setor_bloco_lagartixa_p2.webp
  - grupo_pedreira_setor_bloco_longevidade_p1.webp
  - grupo_pedreira_setor_bloco_mata_mata_p3.webp
  - grupo_pedreira_setor_bloco_meia_parede_p0.webp
  - grupo_pedreira_setor_bloco_meia_parede_p1.webp
  - grupo_pedreira_setor_bloco_meia_parede_p3.webp
  - grupo_pedreira_setor_bloco_mezanino_p0.webp
  - grupo_pedreira_setor_bloco_mezanino_p1.webp
  - grupo_pedreira_setor_bloco_nave_mae_p0.webp
  - grupo_pedreira_setor_bloco_nave_mae_p2.webp
  - grupo_pedreira_setor_bloco_nave_mae_p3.webp
  - grupo_pedreira_setor_bloco_nave_mae_p4.webp
  - grupo_pedreira_setor_bloco_nave_mae_p5.webp
  - grupo_pedreira_setor_bloco_nave_mae_p6.webp
  - grupo_pedreira_setor_bloco_pedra_queimada_p0.webp
  - grupo_pedreira_setor_bloco_sauna_p0.webp
  - grupo_pedreira_setor_bloco_to_de_boa_p1.webp

# Bocaina boulder

- 1 Pressão Enrustida - Qual é qual? Eita setor confuso.
- 4 Canil - qual é o 5. ZAC?
- 6 Cabelin - qual é o 14. La Qualitê?
- 11 Bloco 45o - falta do 19 ao 23.
- 12 Essência - falta 8 Escravos de chó
- Tem outros mapas que mereceriam marcar os finais pra conseguir ficar fácil de
  ver vários boulders

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
