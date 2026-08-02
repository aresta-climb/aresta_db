## 1. Atualização do Schema (Protobuf)

- [x] 1.1 Em `aresta_api/proto/croqui.proto`, adicionar a mensagem `BoundingQuadrado` com os campos `x`, `y` e `lado`.
- [x] 1.2 Em `aresta_api/proto/croqui.proto`, renomear a mensagem `BoundingBox` para `BoundingRetangulo`.
- [x] 1.3 Em `PontoDeInteresse.tipo_area`, renomear a declaração `box` para `retangulo`.
- [x] 1.4 No mesmo bloco `tipo_area`, adicionar `BoundingQuadrado quadrado = 8;`.
- [x] 1.5 Compilar o schema executando o comando base do projeto: `python build.py protos`.

## 2. Refatoração e TDD no Código Python

- [x] 2.1 (TDD) Adicionar testes unitários ou certificar-se de que testes já existentes em `mapas_controller_test.py`, `widget_editor_mapas_test.py` (ou onde os POIs são manipulados) definam as expectativas corretas para `.retangulo` e `.quadrado`, falhando inicialmente.
- [x] 2.2 Buscar e substituir usos de `.box` por `.retangulo` e de `BoundingBox` por `BoundingRetangulo` em todo o código Python (views, scripts, formatadores, etc).
- [x] 2.3 Implementar o novo suporte a `BoundingQuadrado` (e garantir a retrocompatibilidade) nas validações e views, até que os testes do passo 2.1 fiquem verdes.
- [x] 2.4 Executar os testes automatizados via `python build.py test` para assegurar 100% de cobertura de testes conforme PRINCIPIOS.md e aprovar a refatoração.

## 3. TDD e Criação da Rotina de Migração JSON

- [x] 3.1 (TDD) Criar o arquivo de testes da migração na pasta `/migracoes/` (ex: `00XX_migrar_pois_box_para_retangulo_test.py`) que mocke um croqui json com `.box`, prevendo a transformação final para `.retangulo` com o conteúdo intacto, que falhará no início.
- [x] 3.2 Criar o script de migração funcional na pasta `/migracoes/` (ex: `00XX_migrar_pois_box_para_retangulo.py`) seguindo a padronização seqüencial e resolver a falha do teste.
- [x] 3.3 Rodar a cobertura de testes `python build.py coverage` confirmando que 100% das novas linhas da migração estão cobertas.
- [x] 3.4 Aplicar a conversão para arquivos da pasta estática de extração `raw_mapas/*.json` para mantê-los consistentes (via script auxiliar isolado ou regex replace no scratch).

## 4. Atualização da Skill de Agente de ML

- [x] 4.1 Editar o arquivo `.agents/skills/mapa_extrair_pontos_de_interesse/SKILL.md`.
- [x] 4.2 Alterar a documentação dos formatos de bounding areas para: `circular` > `quadrado` > `retangulo` > `area_livre`.
- [x] 4.3 Acrescentar a instrução exigindo que o agente de IA adote um padrão unificado (mesmo raio ou lado relativo a todos os outros POIs daquele tipo no mapa).
