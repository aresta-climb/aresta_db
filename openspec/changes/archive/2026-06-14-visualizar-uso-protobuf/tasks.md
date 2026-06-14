## 1. Setup

- [x] 1.1 Adicionar pacote `graphviz` no arquivo `aresta_api/requirements.txt` e no `requirements.txt` da raiz (se aplicável) e instalar no ambiente virtual.
- [x] 1.2 Documentar a instalação do binário do sistema Graphviz no `README.md` (similar ao que já existe para o `paddlepaddle`).

## 2. Implementação da Biblioteca Core (TDD)

- [x] 2.1 Criar arquivo `scripts/visualizar_uso_protobuf_lib_test.py` definindo a suíte de testes para `DescriptorParser`.
- [x] 2.2 Implementar `DescriptorParser` em `scripts/visualizar_uso_protobuf_lib.py` que lê `indice_pb2` e `croqui_pb2` e extrai todas as mensagens recursivamente, passando nos testes.
- [x] 2.3 Adicionar testes para o módulo `BinaryPbCounter` que lê instâncias protobuf e registra as contagens para "publicados" e "geral".
- [x] 2.4 Implementar `BinaryPbCounter` na biblioteca, alcançando sucesso nos testes.
- [x] 2.5 Adicionar testes cobrindo a lógica de cores de mapa de calor (`HeatmapCalculator`) e a formatação `GraphvizRenderer` para tabelas HTML-like.
- [x] 2.6 Implementar `HeatmapCalculator` e `GraphvizRenderer` garantindo a exportação correta no formato `dot`.

## 3. Integração CLI

- [x] 3.1 Criar e implementar `scripts/visualizar_uso_protobuf.py`, conectando o parser do CLI (`argparse`) às rotinas da biblioteca.
- [x] 3.2 O script CLI deve iterar em `generated/`, extrair as contagens, usar o `GraphvizRenderer` e salvar `croqui.dot`, `croqui.svg`, `indice.dot` e `indice.svg` na pasta `reports/`.
