# TODO

Tarefas ainda a fazer na database.

## Editor
- Muitas melhorias para undo/redo:
  - No editor de mapas, adicionar novos pontos ou remover pontos não está como parte do ctrl+z

## Inspeções
- Inspecionar se tem que converter quadrados para círculos
- Inspecionar se tem como extrair desenhos dos mapas para refazer a parte das extrações de imagens/mapas com maior qualidade.

## MIGRAÇÃO DO ESQUEMA DE MAPAS
- Script para validar que os pontos de interesse todos encontram uma escalada para referenciar
- Por quê as imagens do 'acesso' do baú agora estão incluindo legenda?
- Atualizar a documentação do workflow e skill de extrair mapas.
- Extrair as mensagens de Mapa e sub-mensagens para um arquivo mapa.proto.
- Converter os arquivos .json das pastas de mapas para formato YAML seguindo o proto Mapa.
- Atualizar todas as pastas raw_maps para estar de acordo com os novos formatos

## Geral
- Criar um novo 'partes.proto' e converter todos os partes.json para partes.yaml seguindo esse formato, e atualizar as skills para seguir esse novo proto.
- Coloque um script que duplica imagens caso estiverem sendo usadas em mais de um local no mesmo arquivo .md. E coloque instruções para o modelo referenciar a mesma imagem mais de uma vez caso houverem sub-imagens na imagem.
- OCR/map recognition para mapas gerais também.
- Suportar boulders que tem marcado início e fim (por exemplo 2E no ouroboulder).
- Implementar algum tipo de desambiguação entre id_no_mapa das escaladas e os ids realmente disponíveis no mapa, e ter algum tipo de métrica de saúde sobre isso.
- Corrigir o partes.json para ser um partes.yaml baseado em um partes.proto, e trocar todos para pararem de ser JSON.

## Igarameca

- Criar um super-setor pedra grande pra o mapa geral do complexo pedra grande

## Cambotas

Precisa de MUITO trabalho no croqui de Cambotas pra fazer sentido dele.

## Bombonera

Tem um 8-9 no mapa que temos que ver o que fazer para mapear para a via.