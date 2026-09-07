## Purpose

Define os requisitos e o comportamento esperado do workflow de lançamento do Editor Aresta, assegurando publicação ágil focada no canal Beta por padrão e submissão direta para certificação na Microsoft Store quando requisitado.

## ADDED Requirements

### Requirement: Publicação Padrão no Canal Beta
O workflow de lançamento do Editor Aresta DEVE (SHALL) publicar automaticamente os artefatos compilados e assinados no canal Beta (Cloudflare R2 e AppInstaller), executando uma única compilação PyInstaller quando o parâmetro da Microsoft Store não estiver habilitado.

#### Scenario: Execução padrão do workflow com foco exclusivo em Beta
- **WHEN** o workflow de lançamento for acionado sem marcar a opção `publicar_microsoft_store` (ou com valor `false`)
- **THEN** o sistema executa a compilação exclusiva do canal Beta e publica os artefatos no Cloudflare R2
- **AND** o sistema pula integralmente as etapas de compilação, empacotamento e upload para a Microsoft Store.

### Requirement: Lançamento e Submissão Direta na Microsoft Store
O workflow de lançamento do Editor Aresta DEVE (SHALL) disponibilizar o parâmetro booleano `publicar_microsoft_store` (com valor padrão `false`) que, quando habilitado, aciona a compilação do executável de produção, empacotamento MSIX e submissão direta para certificação na Microsoft Store sem a flag `--noCommit`.

#### Scenario: Execução com lançamento na Microsoft Store ativado
- **WHEN** o workflow de lançamento for disparado com o parâmetro `publicar_microsoft_store` preenchido como `true`
- **THEN** o sistema executa o fluxo do canal Beta com sucesso
- **AND** em seguida compila o executável oficial de produção e gera o pacote MSIX oficial
- **AND** executa a ferramenta `msstore` para publicação sem a opção `--noCommit`, submetendo a atualização imediatamente para revisão e certificação.

#### Scenario: Ausência de submissão em modo rascunho
- **WHEN** qualquer publicação para a Microsoft Store for disparada pelo workflow
- **THEN** o comando executado com `msstore` não inclui o argumento `--noCommit`
- **AND** a submissão não permanece pendente como rascunho manual no painel do Microsoft Partner Center.

### Requirement: Sequenciamento e Atomicidade do Lançamento
O workflow DEVE (SHALL) orquestrar as etapas de build executando primeiro o canal Beta e finalizando a alteração de versão de desenvolvimento (`-dev`) e envio de commits e tags git apenas após a conclusão bem-sucedida de todas as publicações selecionadas.

#### Scenario: Sequenciamento com ambas as publicações ativas
- **WHEN** o workflow for acionado com `publicar_microsoft_store` igual a `true`
- **THEN** a etapa do canal Beta é executada e publicada no Cloudflare R2 antes do início da compilação e publicação na Microsoft Store
- **AND** a criação do commit com a próxima versão `-dev` e o `git push` ocorrem apenas após o sucesso de ambas as publicações.
