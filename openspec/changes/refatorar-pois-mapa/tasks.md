## 1. Atualização do Schema (Protobuf)

- [ ] 1.1 Em `aresta_api/proto/croqui.proto`, adicionar a mensagem `BoundingQuadrado` com os campos `x`, `y` e `lado`.
- [ ] 1.2 Em `aresta_api/proto/croqui.proto`, renomear a mensagem `BoundingBox` para `BoundingRetangulo`.
- [ ] 1.3 Em `PontoDeInteresse.tipo_area`, renomear a declaração `box` para `retangulo`.
- [ ] 1.4 No mesmo bloco `tipo_area`, adicionar `BoundingQuadrado quadrado = 8;`.

## 2. Refatoração de Código Python e Compilação

- [ ] 2.1 Buscar e substituir usos de `.box` por `.retangulo` e de `BoundingBox` por `BoundingRetangulo` em todo o código em Python (views, scripts, formatadores, etc).
- [ ] 2.2 Compilar o schema executando o comando base do projeto: `python build.py protos`.
- [ ] 2.3 Executar os testes automatizados do projeto via `python build.py test` para assegurar que nenhuma chamada a atributo descontinuado (.box) passou despercebida.

## 3. Criação da Rotina de Migração JSON

- [ ] 3.1 Criar o script de migração na pasta `/migracoes/` (ex: `00XX_migrar_pois_box_para_retangulo.py`) usando o ID numérico seguinte livre e os padrões do motor de migração.
- [ ] 3.2 O script deve carregar o modelo do croqui ou iterar pelos JSONs, encontrar as propriedades `"box"`, trocar o nome para `"retangulo"` e persistir os dados originais.
- [ ] 3.3 Criar o arquivo de testes da migração na mesma pasta (ex: `00XX_migrar_pois_box_para_retangulo_test.py`).
- [ ] 3.4 Aplicar uma conversão paralela usando search & replace (ou script no `/scratch`) para a pasta de arquivos estáticos `raw_mapas/*.json` para que novas execuções não puxem arquivos quebrados.

## 4. Atualização da Skill de Agente de ML

- [ ] 4.1 Editar o arquivo `.agents/skills/mapa_extrair_pontos_de_interesse/SKILL.md`.
- [ ] 4.2 Alterar a documentação dos formatos de bounding areas para: `circular` > `quadrado` > `retangulo` > `area_livre`.
- [ ] 4.3 Acrescentar a instrução de extração solicitando que o agente selecione um tamanho padrão (raio ou lado) aplicável a todos os marcadores de rotas e use isso de forma consistente.
