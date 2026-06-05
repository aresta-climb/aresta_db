## Why

Atualmente, o processo de deploy não verifica se os IDs de mapa referenciados nas escaladas (`id_no_mapa`, `id_no_mapa_meio`, `id_no_mapa_fim`) realmente existem nos mapas definidos para aquele setor ou grupo. Isso pode levar a erros de interface ou informações faltantes no aplicativo frontend quando um autor comete um erro de digitação ou esquece de definir um ponto de interesse.

## What Changes

- **Validação de IDs de Mapa**: Implementação de uma verificação rigorosa que garante que toda referência de ID de mapa em uma escalada aponte para um ID válido em pelo menos um dos mapas disponíveis no contexto (Setor ou Grupo).
- **Relatório de Erros Agregado**: A compilação não parará no primeiro erro de ID inválido. Em vez disso, coletará todos os erros de um croqui e os exibirá de uma só vez.
- **Resiliência do Pipeline**: O script de deploy continuará tentando compilar todos os croquis da base de dados, mesmo que alguns falhem na validação, reportando o saldo final de sucessos e falhas.

## Capabilities

### New Capabilities
- `valida-ids-mapa`: Validação de integridade referencial entre escaladas e pontos de interesse nos mapas durante o processo de deploy.

### Modified Capabilities
Nenhuma.

## Impact

- `scripts/deploy_generated.py`: Atualização do fluxo principal de deploy para incluir a nova etapa de validação e o relatório final de erros.
- `scripts/preparar_submissao_lib.py`: Provável local para a implementação da lógica de validação seguindo o princípio "Library-First".
- Processo de CI/CD: O deploy passará a falhar caso existam inconsistências nos dados dos croquis.
