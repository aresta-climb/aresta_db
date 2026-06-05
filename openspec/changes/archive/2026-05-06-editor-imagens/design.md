## Context

O script `scripts/editar_imagens.py` é uma ferramenta baseada em PyQt6 que permite edição em lote de imagens (crop, rotação, máscaras). Atualmente, ele é uma aplicação autônoma completa (`QMainWindow`). Para integrá-lo ao Editor Aresta, precisamos extrair a lógica da interface para um widget reutilizável e garantir que ele possa operar em dois modos: autônomo e integrado.

## Goals / Non-Goals

**Goals:**
- Refatorar `scripts/editar_imagens.py` para separar a lógica de `MainWindow` em um `WidgetEditorImagens`.
- Integrar o `WidgetEditorImagens` na `JanelaPrincipal` do editor.
- Sincronizar o salvamento das imagens com o botão de salvamento principal do editor.
- Manter a funcionalidade de script autônomo.
- Seguir o princípio **Library-First**: o widget deve ser uma peça independente.

**Non-Goals:**
- Adicionar novas funcionalidades de edição de imagem além das já existentes (crop, rotação, máscaras).
- Alterar o formato de armazenamento das imagens (continuará sendo WebP/PNG/JPG na pasta `imagens`).

## Decisions

### 1. Extração para `editor/views/widget_editor_imagens.py`
**Decisão:** Mover a lógica principal de interface do `scripts/editar_imagens.py` para um novo arquivo `editor/views/widget_editor_imagens.py`.
**Racional:** Segue o princípio de organização do projeto onde as visões residem em `editor/views`. Facilita a importação tanto pelo script quanto pela janela principal.

### 2. Controle de Visibilidade do Botão Salvar
**Decisão:** O `WidgetEditorImagens` receberá um parâmetro `modo_integrado` (bool) no construtor. Se `True`, ele oculta o botão "Salvar TUDO" interno.
**Racional:** Evita duplicidade de botões de salvamento quando integrado no Editor, mantendo a experiência limpa e consistente com o resto do aplicativo.

### 3. API de Salvamento Exposta
**Decisão:** O widget terá um método público `salvar_alteracoes()` que realiza a persistência no disco.
**Racional:** Permite que a `JanelaPrincipal` chame o salvamento de todas as abas (Dados, Mapas, Imagens) de forma unificada.

### 4. Gestão de Estado via `PageState`
**Decisão:** Manter a classe `PageState` para gerenciar as alterações em memória antes do salvamento.
**Racional:** A lógica atual já funciona bem e permite desfazer alterações em uma imagem específica (Reset) antes de persistir no disco.

## Estratégia de Testes (TDD)

Seguindo estritamente o `PRINCIPIOS.md`, a implementação seguirá o ciclo **Red-Green-Refactor**:

1. **Testes de Integração Primeiro**: Antes de refatorar o widget, criaremos testes de integração que validam a presença da aba de imagens na `JanelaPrincipal` e o contrato de salvamento global.
2. **Ciclo TDD para o Widget**:
   - Criar `editor/views/widget_editor_imagens_test.py` com testes falhando para as novas responsabilidades (modo integrado, API de salvamento).
   - Implementar o código mínimo para fazer os testes passarem.
   - Refatorar para garantir a qualidade do código extraído do script original.
3. **Validação de Regressão**: O script autônomo `scripts/editar_imagens.py` também deve ter seu próprio arquivo de teste `scripts/editar_imagens_test.py` (ou atualizar o existente) para garantir que a refatoração não quebrou o uso via CLI.

## Risks / Trade-offs

- **[Risco] Acoplamento com a Janela Principal** → **Mitigação**: O widget deve interagir com a janela principal apenas via sinais ou métodos públicos bem definidos, mantendo-se autossuficiente para testes.
- **[Risco] Performance com muitas imagens** → **Mitigação**: As imagens são carregadas sob demanda quando selecionadas na lista, mantendo o uso de memória controlado.

## Migration Plan

1. **[TDD]** Criar testes de integração falhando para a nova aba "Imagens" na `JanelaPrincipal`.
2. **[TDD]** Criar `editor/views/widget_editor_imagens_test.py` com a definição do contrato esperado.
3. Criar `editor/views/widget_editor_imagens.py` (Green phase).
4. Atualizar `editor/views/janela_principal.py` para satisfazer os testes de integração.
5. Atualizar `scripts/editar_imagens.py` e validar com testes de regressão.
