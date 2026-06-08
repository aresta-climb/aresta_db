## Why

Atualmente, a mensagem `ResumoCroqui` não possui a informação de coordenada geográfica do local de escalada. Essa ausência impede ou dificulta a exibição em mapa de todos os croquis disponíveis no índice de forma eficiente na tela inicial do aplicativo, já que para se ter a coordenada de cada local hoje seria necessário baixar o binário completo (`compilado.binarypb`) de cada croqui.

## What Changes

- O protobuf do índice passará a expor os dados de latitude e longitude do croqui.
- Adição da estrutura `Coordenada` na mensagem `ResumoCroqui`, através da importação de `croqui.proto`.
- O compilador de croquis passará a povoar automaticamente essa coordenada no índice com base na localização do primeiro pico informada no `croqui.yaml`.

## Capabilities

### New Capabilities
- `resumo-croqui-mapa`: Suporte de coordenadas a nível de índice do croqui.

### Modified Capabilities

## Impact

- `aresta_api/proto/indice.proto`: Inclusão do import de `croqui.proto` e do campo `localizacao` (tipo `Coordenada`) na mensagem `ResumoCroqui`.
- `scripts/deploy_generated.py`: Passará a preencher o campo com os dados de `localizacao` provindos do yaml lido (que já estarão em formato E7 / `sint32`).
- As aplicações frontend (app) que consomem o índice passarão a poder utilizar essa propriedade para dispor pinos no mapa.

## Constraints & Principles

**Conformidade com PRINCIPIOS.md:**
- **TDD (Test-Driven Development) Imperativo:** A implementação *deverá* seguir o ciclo Red-Green-Refactor rigorosamente. Antes de qualquer código ser alterado no `scripts/deploy_generated.py`, os testes unitários equivalentes (`scripts/deploy_generated_test.py` se houver, ou outro teste cobrindo a compilação do índice) *deverão* ser escritos primeiro (vistos falhar) e refatorados em seguida.
- **100% Unit Test Coverage:** Todo novo caminho de lógica inserido para repassar a `localizacao` (com e sem a chave presente no dict original) deve ser 100% coberto por testes.
