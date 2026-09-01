## Why

A conexão direta e exclusiva via rede local (LAN) para testar e revisar croquis experimentais no celular é extremamente frágil em ambientes do mundo real (bloqueios por isolamento de cliente em Wi-Fi corporativo ou de visitantes, sub-redes distintas, firewalls locais do sistema operacional como o Windows Defender, ou celulares conectados em dados móveis 4G/5G). Além disso, não há suporte a recarregamento automático em tempo real (sincronização ao vivo) nem compartilhamento remoto de prévias entre autores e revisores que estejam fisicamente em locais diferentes.

Esta alteração introduz uma solução híbrida robusta baseada em uma biblioteca modular de retransmissão: conexão local primária com alternância transparente para um retransmissor na nuvem (Cloudflare Worker em `previa.arestaclimb.com`), pareamento simplificado por código alfanumérico legível de 8 caracteres em Base36 (`k9x2-p83a`) e sincronização instantânea em tempo real através de canal WebSocket de eventos.

## What Changes

- **Biblioteca de Códigos de Sessão (`codigo_sessao.py`)**: Criação de biblioteca isolada e autossuficiente para geração, validação e normalização de identificadores curtos de 8 caracteres alfanuméricos em Base36 (`[0-9a-z]`, ex: `k9x2-p83a`).
- **Biblioteca de Túnel de Retransmissão (`tunel_retransmissor.py`)**: Criação de biblioteca modular para o cliente WebSocket de saída do Editor Desktop, gerenciando o ciclo de vida do túnel com `previa.arestaclimb.com`, troca de batimentos cardíacos (*heartbeat*) e resposta a requisições de arquivos via streaming em memória.
- **Serviço Retransmissor em Nuvem (`aresta_backend/cloudflare/previa`)**: Implementação de retransmissor leve na Cloudflare (`previa.arestaclimb.com`) que atua como intermediário de descoberta e proxy reverso de streaming HTTP-para-WebSocket, operando 100% em memória RAM sem persistência em banco de dados ou storage, acompanhado de documentação completa de configuração de DNS e deploy.
- **Resolução Híbrida Inteligente (Rede Local em Primeiro Lugar)**: O aplicativo móvel executa uma disputa de conexão em paralelo: consulta os metadados do retransmissor, testa o IP local do editor com tempo limite curto e, caso responda, utiliza a rede local para taxa máxima de transferência; caso contrário, utiliza o retransmissor na nuvem de forma transparente.
- **Sincronização em Tempo Real (Recarregamento ao Vivo)**: Emissão de eventos leves via WebSocket a cada compilação de croqui no editor, instruindo o aplicativo móvel a invalidar o cache em memória e baixar apenas os arquivos modificados.
- **Compartilhamento Remoto de Prévias**: Suporte a links diretos no formato `https://previa.arestaclimb.com/<codigo>`, permitindo que revisores remotos abram a prévia do croqui em tempo real diretamente no aplicativo móvel.
- **Conformidade com os Princípios de Engenharia**: Arquitetura orientada a bibliotecas isoladas (Library-First), 100% de cobertura de testes unitários (`*_test.py` acompanhando cada módulo), desenvolvimento orientado a testes (TDD Red-Green-Refactor) e testes de integração de fronteira em primeiro lugar.

## Capabilities

### New Capabilities
- `retransmissor-nuvem-previa`: Especificação do serviço de retransmissão na nuvem (`aresta_backend/cloudflare/previa`) para gerenciamento de sessões efêmeras, anúncio de metadados de rede, streaming reverso em memória e guia de configuração.
- `cliente-sincronizacao-ao-vivo`: Especificação da biblioteca cliente (Desktop e Móvel) para pareamento por código/link, resolução híbrida de rede e recepção de eventos de sincronização em tempo real.

### Modified Capabilities
- `servidor-celular`: Atualização dos requisitos do servidor local do Editor Desktop para incorporar o cliente de túnel de saída e a emissão de eventos push de recarregamento.

## Impact

- **Editor Desktop (`aresta_db`)**: Novos módulos modulares `editor/core/codigo_sessao.py`, `editor/core/tunel_retransmissor.py` e testes associados `*_test.py` com 100% de cobertura; atualização de `servidor_celular.py` e da interface `dialogo_conexao_celular.py`.
- **Infraestrutura em Nuvem (`aresta_backend/cloudflare/previa`)**: Novo projeto Cloudflare Worker com TypeScript, testes automatizados e manual de configuração e deploy no Cloudflare Dashboard.
- **Aplicativo Móvel (`aresta_app`)**: Atualização do serviço `EditorDeCroqui` no Flutter com suporte à resolução híbrida, digitação manual normalizada de código e tratamento de links diretos.
