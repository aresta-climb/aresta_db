# Tarefas (Tasks): Foto de Capa para Setores e Grupos

## 1. Schema Protobuf & Compilação

- [ ] 1.1 Atualizar `aresta_api/proto_validacao_test.py` com testes para o campo `caminho_imagem_capa` em `Setor` e `Grupo` e verificar falha inicial (TDD Red)
- [ ] 1.2 Adicionar `string caminho_imagem_capa = 5` nas mensagens `Setor` e `Grupo` em `aresta_api/proto/croqui.proto` com as anotações `IMAGEM`, `CAMINHO` e `image/webp`
- [ ] 1.3 Executar `python aresta_api/build.py -f` e verificar que os stubs Python e Dart são gerados com sucesso e os testes de validação passam (TDD Green)

## 2. Rastreamento no Ciclo de Vida e Pipeline de Deploy

- [ ] 2.1 Adicionar teste em `editor/core/imagens_croqui_test.py` verificando a extração de `caminho_imagem_capa` e detecção de imagens órfãs
- [ ] 2.2 Atualizar `extrair_caminhos_imagens` em `editor/core/imagens_croqui.py` para incluir `caminho_imagem_capa` e verificar aprovação dos testes
- [ ] 2.3 Atualizar `scripts/preparar_submissao_lib.py` e `scripts/deploy_generated.py` para incluir `caminho_imagem_capa` nos coletores de arquivos externos e validar com `scripts/preparar_submissao_lib_test.py`

## 3. Interface do Editor (UI & Limite de 1 Megapixel)

- [ ] 3.1 Adicionar testes em `editor/views/widget_campo_imagem_test.py` validando o parâmetro de área máxima customizável
- [ ] 3.2 Atualizar `editor/views/widget_campo_imagem.py` e `editor/views/protobuf_widget_factory.py` para aplicar o limite de 1 Megapixel (`AREA_MAXIMA_ESCALADA`) em campos de capa
- [ ] 3.3 Adicionar testes em `editor/views/widget_editor_dados_test.py` garantindo que `caminho_imagem_capa` seja posicionado no topo antes de `nome` em formulários de Setor e Grupo
- [ ] 3.4 Ajustar a ordenação de campos em `editor/views/widget_editor_dados.py` para renderizar `caminho_imagem_capa` na primeira posição dos campos principais e verificar os testes

## 4. Script Utilitário de Extração de Capas

- [ ] 4.1 Criar `scripts/extrair_capas_markdown_test.py` com testes cobrindo extração da imagem de abertura, promoção para frontmatter, remoção da tag do markdown, teto de 1 MP e idempotência
- [ ] 4.2 Implementar `scripts/extrair_capas_markdown.py` atendendo a todos os testes unitários
- [ ] 4.3 Executar o script utilitário sobre os croquis em `database/` para promover as capas existentes

## 5. Verificação de Integração e Deploy

- [ ] 5.1 Executar a suíte completa de testes do editor (`pytest editor/`) e verificar 100% de aprovação
- [ ] 5.2 Executar `python scripts/deploy_generated.py` e confirmar geração limpa de `.binarypb` com zero erros e avisos
