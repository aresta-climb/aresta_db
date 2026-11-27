# Spec Delta

## ADDED Requirements

### Requirement: Registro Canônico Unificado de Ferramentas MCP Compartilhado com Modo Headless
O Editor Aresta MUST centralizar o registro das ferramentas MCP de comandos, visão estrutural/mapas, ciclo de vida, conhecimento e betas em um registrador único compartilhado entre a interface gráfica (modos Padrão e Local) e o Modo Headless, dispensando widgets visuais para todas as ferramentas que não capturam viewport de janela.

#### Scenario: Paridade de ferramentas de domínio entre modo gráfico e modo headless
- **WHEN** uma sessão MCP é inicializada em modo *headless* sobre um croqui aberto
- **THEN** todas as ferramentas de mutação (`aresta_alterar_campo`, `aresta_alterar_em_lote`, `aresta_adicionar_repeated`, `aresta_remover_repeated`, `aresta_mover_repeated`, `aresta_migrar_escalada`, `aresta_migrar_setor`, referências e imagens), inspeção/visão de mapas (`aresta_obter_arvore`, `aresta_listar_escaladas`, `aresta_renderizar_mapa`), conhecimento (`aresta_obter_esquema_proto`, `aresta_listar_skills`, `aresta_ler_skill`) e ciclo de vida (`aresta_compilar`, `aresta_salvar`, `aresta_status_workspace`) ficam disponíveis e executam diretamente em memória na mesma thread

#### Scenario: Retorno descritivo ao capturar viewport de janela em modo headless
- **WHEN** um cliente invoca `aresta_capturar_canvas` em uma sessão *headless* onde não há widgets de interface gráfica instanciados
- **THEN** o servidor MCP retorna `isError: True` com mensagem clara informando que o viewport gráfico não está disponível em modo *headless* e orientando o uso de `aresta_renderizar_mapa` ou `aresta_obter_arvore`
