## Context

O padrão MVC foi adotado para a camada de interface do Editor Aresta. Atualmente, a pasta `editor/views/` contém classes que quebram esse padrão ao realizar operações de banco de dados, storage direto e orquestração de workers (ex: `area_principal.py`, `tela_de_carregamento.py`, `dialogo_conexao_celular.py`, `dialogo_busca_croqui.py`).

## Goals / Non-Goals

**Goals:**
- Proteger a integridade da pasta `views` para que contenha apenas código de interface puro e aderente ao MVC.
- Organizar a base de código separando claramente as Views puras das Views legadas que atuam como Controllers/Services.

**Non-Goals:**
- Refatorar a lógica interna dessas views legadas neste momento. O foco é a reorganização do namespace.

## Decisions

- **Movimentação para `legacy_views`**: As quatro classes problemáticas serão movidas para `editor/legacy_views/`, juntamente com seus respectivos arquivos de teste `*_test.py`.
- **Refatoração Isolada**: Optamos por apenas mover os arquivos agora para limpar a pasta `views` imediatamente, deixando a refatoração interna (extração de Controllers) para futuros Pull Requests independentes.
- **Busca e Substituição de Imports**: Usaremos ferramentas de busca no repositório para substituir referências a `editor.views.<arquivo>` para `editor.legacy_views.<arquivo>` de forma atenta.

## Risks / Trade-offs

- **[Risco] Erros de Importação (ImportError)** → **[Mitigação]** Executar a suíte de testes unitários e de integração (`pytest`) após as alterações e fazer uma revisão global nos imports do `main.py` e utilitários.
