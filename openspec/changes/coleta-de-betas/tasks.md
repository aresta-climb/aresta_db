## 1. Atualização do Schema Protobuf (TDD First)

- [ ] 1.1 Escrever testes unitários para as novas propriedades de mídia no compilador de croquis (garantindo falha inicial - Red).
- [ ] 1.2 Atualizar arquivo `croqui.proto` para adicionar as messages `MidiaBeta` e `MetaBeta` vinculadas à `Escalada`. Garantir estritamente: enums encapsulados com `INDEFINIDO = 0` e oneofs encapsulados, conforme `PRINCIPIOS.md`.
- [ ] 1.3 Modificar os scripts de compilação (parser YAML->Proto) para processar o bloco `betas` e fazer os testes passarem (Green/Refactor com 100% coverage).

## 2. Worker Python: Biblioteca e TDD (Extração)

- [ ] 2.1 Inicializar um módulo/biblioteca independente (Library-First) para a busca de mídias e configurar a suíte de testes.
- [ ] 2.2 TDD (Integração Primeiro): Escrever testes de integração falhos mockando os retornos do YouTube Data API v3.
- [ ] 2.3 Implementar o Google API Client para YouTube (Green/Refactor).
- [ ] 2.4 TDD: Escrever testes de integração falhos para as buscas no Vertex AI Search e `duckduckgo-search` (`instagram.com`).
- [ ] 2.5 Implementar os clientes Vertex AI e DuckDuckGo (Green/Refactor) mantendo 100% de coverage nas fronteiras.
- [ ] 2.6 TDD: Testar unitariamente e implementar a deduplicação cruzada de URLs idênticas do Google e DDG (preservando flags de agregação).

## 3. Integração de Inteligência (Sub-Agentes)

- [ ] 3.1 TDD: Escrever testes unitários para as funções que envelopam o prompt e formatam o JSON esperado da LLM.
- [ ] 3.2 Implementar a chamada ao provedor LLM processando os candidatos em batch (Green/Refactor).
- [ ] 3.3 Processar outputs forçando JSON-schema para extrair `llm_confidence_score`, `llm_reasoning` e `resumo_do_movimento` sob 100% de coverage.
- [ ] 3.4 Gerar o arquivo temporário `betas_pendentes.binarypb` de forma testável e validada.

## 4. Aba de Curadoria (Editor PyQt)

- [ ] 4.1 TDD: Escrever testes (Red) para a lógica do Controller da UI, mockando chamadas HTTP para o download de imagens.
- [ ] 4.2 Criar a interface de usuário (Tab) no Editor PyQt para ler o `betas_pendentes.binarypb` (Green/Refactor).
- [ ] 4.3 Implementar worker assíncrono para buscar URLs HTTP das thumbnails.
- [ ] 4.4 Desenvolver a lógica visual (Checkboxes, ordenação por score LLM, fallback genérico para ícone do Instagram) garantindo isolamento da lógica de negócios e testes limpos.

## 5. Edição In-Place e Workflow

- [ ] 5.1 TDD: Escrever testes unitários exaustivos (Red) usando arquivos Markdown simulados para garantir que nenhuma estrutura existente seja corrompida na persistência.
- [ ] 5.2 Desenvolver a lógica do botão "Salvar": Parsear arquivo `grupo_*.md`, injetar a key YAML `betas` in-place e salvar (Green/Refactor 100% seguro).
- [ ] 5.3 Criar o arquivo de workflow final `.agents/workflows/coletar_betas.md` descrevendo como invocar o pipeline pelo Antigravity.
