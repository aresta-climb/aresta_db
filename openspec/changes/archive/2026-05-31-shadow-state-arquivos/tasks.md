## 1. Protobuf e Schemas

- [x] 1.1 Atualizar `croqui.proto`: Adicionar blocos `extensions 1000 to max;` nas mensagens `ArquivoMarkdown`, `ArquivoSetor` e `ArquivoGrupo`.
- [x] 1.2 Atualizar `croqui.proto`: Definir extensões globais `caminho_original = 1000;` e `caminho_novo = 1001;` que estendam os três tipos de arquivos acima (ou definir campos com formato invisível, se Python reclamar muito).
- [x] 1.3 Compilar os protobufs (rodar `python build.py` na pasta aresta_api) para gerar os bindings.

## 2. Refatoração do Ciclo de Persistência

- [x] 2.1 Teste primeiro: Atualizar `preparar_submissao_lib_test.py` para assegurar que a função genérica `limpar_arquivos_nao_utilizados` trata imagens e `.md` (TDD).
- [x] 2.2 Atualizar `preparar_submissao_lib.py`: Renomear `limpar_imagens_nao_utilizadas` e adequá-la para passar no teste acima.
- [x] 2.3 Teste primeiro: Criar `deploy_generated_test.py` com um YAML sujo mockado, validando que o compilador levanta erro nas extensões `caminho_original` e `caminho_novo` (TDD).
- [x] 2.4 Atualizar `deploy_generated.py`: Adicionar a validação estrita no loop principal que quebra a compilação caso vazem extensões.
- [x] 2.5 Teste primeiro: Criar/Atualizar testes para `CroquiModel` atestando que `CroquiModel.salvar` interage corretamente com o Shadow State em disco e limpa as extensões em memória (TDD).
- [x] 2.6 Implementar `CroquiModel.salvar`: Ler as extensões, descarregar no "caminho_novo", deletar do "caminho_original", e fazer `ClearExtension` para passar nos testes.

## 3. Simplificação do Editor e MVC

- [x] 3.1 Teste primeiro: Atualizar `ReadOnlyProxyTest` certificando-se de que acessar `.Extensions` levanta exceção (para impedir Views de sujar a extensão) (TDD).
- [x] 3.2 Atualizar `ReadOnlyProxy` em `editor/models/readonly_proxy.py`: Bloquear escrita no `ExtensionDict` de uma mensagem. setters e passe no teste.
- [x] 3.3 Teste primeiro: Criar testes para os novos Comandos de Protobuf que atualizarão o Shadow State (TDD).
- [x] 3.4 Criar os comandos em `comandos_protobuf.py` (ou similiares) para mutar as extensões `caminho_original` e `caminho_novo` de forma MVC-compliant e satisfazer os testes.
- [x] 3.5 Limpar `area_principal.py` e `widget_editor_dados.py`: Remover todo tracking antigo (`arquivos_carregados`, `caminhos_originais`).
- [x] 3.6 Atualizar `widget_editor_dados.py`: Ao sujar o texto, despachar o comando criado em 3.4. Ao ler `ONEOF_CONTEUDO`, priorizar a leitura de `caminho_novo`.
- [x] 3.7 Adaptar testes de Views que falharem após a remoção dos dicionários (TDD Refactor).
