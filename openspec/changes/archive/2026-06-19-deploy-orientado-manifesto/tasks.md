## 1. Protobufs
- [x] 1.1 Criar `aresta_api/proto/serving.proto` com a mensagem `ManifestoServing`.
- [x] 1.2 Atualizar `build.py` para compilar o novo `serving.proto`.

## 2. Geração do Manifesto
- [x] 2.1 Adicionar em `scripts/deploy_generated.py` a lógica recursiva para calcular o sha256 de toda a pasta `generated/` ao fim da compilação.
- [x] 2.2 Serializar e salvar a mensagem `ManifestoServing` gerada no arquivo `generated/arquivos_serving.binarypb`.
- [x] 2.3 Atualizar ou adicionar testes unitários no `deploy_generated_test.py` provando a criação correta deste manifesto.

## 3. Script Python de Deploy (TDD-First)
- [x] 3.1 Criar diretório `serving/` e `serving/requirements-serving.txt` (com `boto3`, `requests` e `protobuf`).
- [x] 3.2 Criar `update_serving_test.py` com testes exaustivos para atingir 100% de coverage usando Moto (S3 Mock) e requests-mock, seguindo as diretrizes do PRINCIPIOS.md.
- [x] 3.3 Implementar a classe central em `update_serving.py` que baixa o manifesto remoto.
- [x] 3.4 Desenvolver a lógica de "Full Deploy Fallback" (se remoto não existe, chama `git checkout HEAD -- generated/` e sobe tudo).
- [x] 3.5 Desenvolver a lógica de "Delta" (compara remoto com local, orquestrando lazy-download no Git via comando único e fazendo uploads via Boto3).
- [x] 3.6 Adicionar requisição de invalidação de CDN chamando a API de Purge Cache do Cloudflare internamente no `update_serving.py`, focada apenas nos manifestos.

## 4. Pipeline do GitHub Actions
- [x] 4.1 Limpar `deploy.yml`, instalando `requirements-serving.txt`.
- [x] 4.2 Alterar a chamada bash para invocar o `python serving/update_serving.py`.
